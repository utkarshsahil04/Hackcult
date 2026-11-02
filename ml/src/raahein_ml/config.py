"""Load and hash the repository-owned recognition configuration."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from raahein_ml.schemas import ConfigurationError

MODEL_NAMES = ("siglip", "dinov2", "clip")
REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_MODELS = {
    "siglip": (
        "google/siglip-base-patch16-224",
        "7fd15f0689c79d79e38b1c2e2e2370a7bf2761ed",
        "siglip",
        768,
    ),
    "dinov2": (
        "facebook/dinov2-base",
        "f9e44c814b77203eaa57a6bdbbd535f21ede1415",
        "dinov2",
        768,
    ),
    "clip": (
        "openai/clip-vit-base-patch32",
        "3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268",
        "clip",
        512,
    ),
}


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def semantic_hash(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def semantic_csv_hash(path: Path) -> str:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    normalized = [
        {key: (value or "").strip() for key, value in sorted(row.items())}
        for row in rows
    ]
    normalized.sort(key=canonical_json_bytes)
    return semantic_hash(normalized)


@dataclass(frozen=True, slots=True)
class ModelSpec:
    name: str
    model_id: str
    revision: str
    adapter: str
    dimension: int
    preprocessing: Mapping[str, object]

    @property
    def processor_hash(self) -> str:
        return semantic_hash(dict(self.preprocessing))


@dataclass(frozen=True, slots=True)
class PathsConfig:
    canonical_monuments: Path
    source_catalog: Path
    manifest: Path
    artifacts: Path
    embedding_cache: Path


@dataclass(frozen=True, slots=True)
class IndexConfig:
    kind: str
    aggregation_top_n: int
    search_all_gallery: bool


@dataclass(frozen=True, slots=True)
class FusionConfig:
    method: str
    rrf_k: int
    weights: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class SplitConfig:
    minimum_gallery: int
    maximum_gallery: int
    calibration_per_class: int
    test_per_class: int


@dataclass(frozen=True, slots=True)
class CalibrationConfig:
    maximum_ood_false_acceptance: float
    minimum_winner_models: int
    calibration_negative_count: int
    test_negative_count: int


@dataclass(frozen=True, slots=True)
class EvaluationConfig:
    independent_positive_count: int


@dataclass(frozen=True, slots=True)
class MLConfig:
    schema_version: int
    config_path: Path
    repository_root: Path
    config_hash: str
    device: str
    allow_cpu: bool
    mixed_precision: bool
    paths: PathsConfig
    models: Mapping[str, ModelSpec]
    index: IndexConfig
    fusion: FusionConfig
    split: SplitConfig
    calibration: CalibrationConfig
    evaluation: EvaluationConfig

    @property
    def canonical_monument_ids(self) -> tuple[str, ...]:
        return load_canonical_monument_ids(self.paths.canonical_monuments)

    @property
    def canonical_monuments_hash(self) -> str:
        with self.paths.canonical_monuments.open("r", encoding="utf-8") as handle:
            return semantic_hash(json.load(handle))


def find_repository_root(start: Path) -> Path:
    start = start.resolve()
    candidates = (start, *start.parents)
    for candidate in candidates:
        canonical = candidate / "backend" / "app" / "db" / "seed_data" / "monuments.json"
        if canonical.is_file() and (candidate / "ml").is_dir():
            return candidate
    raise ConfigurationError(f"could not locate repository root from {start}")


def load_canonical_monument_ids(path: Path) -> tuple[str, ...]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            rows = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"cannot read canonical monuments: {path}") from exc
    if not isinstance(rows, list) or not rows:
        raise ConfigurationError("canonical monument file must be a non-empty list")
    try:
        slugs = [str(row["slug"]) for row in rows]
    except (KeyError, TypeError) as exc:
        raise ConfigurationError("every canonical monument requires a slug") from exc
    if len(slugs) != len(set(slugs)):
        raise ConfigurationError("canonical monument slugs must be unique")
    return tuple(sorted(slugs))


def _mapping(raw: object, name: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ConfigurationError(f"{name} must be a mapping")
    return raw


def _relative_path(repository_root: Path, raw: object, name: str) -> Path:
    path = Path(str(raw))
    if path.is_absolute():
        raise ConfigurationError(f"{name} must be repository-relative")
    resolved = (repository_root / path).resolve()
    try:
        resolved.relative_to(repository_root)
    except ValueError as exc:
        raise ConfigurationError(f"{name} escapes the repository") from exc
    return resolved


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"invalid boolean value: {value}")


def _require_bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ConfigurationError(f"{name} must be a YAML boolean")
    return value


def load_config(
    path: str | Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> MLConfig:
    environment = os.environ if environ is None else environ
    configured_path = path or environment.get("RAAHEIN_ML_CONFIG")
    if configured_path is None:
        repository_root = find_repository_root(Path.cwd())
        config_path = repository_root / "ml" / "config" / "models.yaml"
    else:
        candidate = Path(configured_path).expanduser()
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        config_path = candidate.resolve()
        repository_root = find_repository_root(config_path.parent)

    try:
        with config_path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"cannot read ML config: {config_path}") from exc
    raw = _mapping(loaded, "config")
    paths_raw = _mapping(raw.get("paths"), "paths")
    required_paths = {
        "canonical_monuments",
        "source_catalog",
        "manifest",
        "artifacts",
        "embedding_cache",
    }
    if not required_paths.issubset(paths_raw):
        raise ConfigurationError("paths is missing a required repository-relative path")
    models_raw = _mapping(raw.get("models"), "models")
    if tuple(models_raw) != MODEL_NAMES:
        raise ConfigurationError(f"models must be ordered exactly as {MODEL_NAMES}")

    models: dict[str, ModelSpec] = {}
    for name in MODEL_NAMES:
        model = _mapping(models_raw[name], f"models.{name}")
        revision = str(model.get("revision", ""))
        if not REVISION_PATTERN.fullmatch(revision):
            raise ConfigurationError(f"models.{name}.revision must be a 40-character commit")
        dimension = int(model.get("dimension", 0))
        if dimension <= 0:
            raise ConfigurationError(f"models.{name}.dimension must be positive")
        models[name] = ModelSpec(
            name=name,
            model_id=str(model.get("model_id", "")),
            revision=revision,
            adapter=str(model.get("adapter", "")),
            dimension=dimension,
            preprocessing=_mapping(model.get("preprocessing"), f"models.{name}.preprocessing"),
        )
        expected_model_id, expected_revision, expected_adapter, expected_dimension = (
            EXPECTED_MODELS[name]
        )
        if (
            models[name].model_id,
            models[name].revision,
            models[name].adapter,
            models[name].dimension,
        ) != (
            expected_model_id,
            expected_revision,
            expected_adapter,
            expected_dimension,
        ):
            raise ConfigurationError(f"models.{name} differs from the frozen checkpoint contract")

    device = environment.get("RAAHEIN_ML_DEVICE", str(raw.get("device", "cuda"))).strip()
    allow_cpu = _require_bool(raw.get("allow_cpu", False), "allow_cpu")
    if "RAAHEIN_ML_ALLOW_CPU" in environment:
        allow_cpu = _parse_bool(environment["RAAHEIN_ML_ALLOW_CPU"])
    if device == "cpu" and not allow_cpu:
        raise ConfigurationError(
            "CPU recognition requires explicit RAAHEIN_ML_ALLOW_CPU=true development config"
        )
    if not (device == "cpu" or device.startswith("cuda")):
        raise ConfigurationError("device must be cpu or a CUDA device")

    artifacts = _relative_path(repository_root, paths_raw["artifacts"], "paths.artifacts")
    artifact_override = environment.get("RAAHEIN_ML_ARTIFACT_DIR")
    if artifact_override:
        override_path = Path(artifact_override).expanduser()
        artifacts = (
            override_path.resolve()
            if override_path.is_absolute()
            else (repository_root / override_path).resolve()
        )

    index_raw = _mapping(raw.get("index"), "index")
    fusion_raw = _mapping(raw.get("fusion"), "fusion")
    split_raw = _mapping(raw.get("split"), "split")
    calibration_raw = _mapping(raw.get("calibration"), "calibration")
    evaluation_raw = _mapping(raw.get("evaluation"), "evaluation")
    weights_raw = _mapping(fusion_raw.get("weights"), "fusion.weights")
    if set(weights_raw) != set(MODEL_NAMES):
        raise ConfigurationError("fusion weights must name all configured models")

    config = MLConfig(
        schema_version=int(raw.get("schema_version", 0)),
        config_path=config_path,
        repository_root=repository_root,
        config_hash=semantic_hash(raw),
        device=device,
        allow_cpu=allow_cpu,
        mixed_precision=_require_bool(raw.get("mixed_precision", True), "mixed_precision"),
        paths=PathsConfig(
            canonical_monuments=_relative_path(
                repository_root, paths_raw["canonical_monuments"], "paths.canonical_monuments"
            ),
            source_catalog=_relative_path(
                repository_root, paths_raw["source_catalog"], "paths.source_catalog"
            ),
            manifest=_relative_path(repository_root, paths_raw["manifest"], "paths.manifest"),
            artifacts=artifacts,
            embedding_cache=_relative_path(
                repository_root, paths_raw["embedding_cache"], "paths.embedding_cache"
            ),
        ),
        models=models,
        index=IndexConfig(
            kind=str(index_raw.get("kind")),
            aggregation_top_n=int(index_raw.get("aggregation_top_n", 0)),
            search_all_gallery=_require_bool(
                index_raw.get("search_all_gallery", False), "index.search_all_gallery"
            ),
        ),
        fusion=FusionConfig(
            method=str(fusion_raw.get("method")),
            rrf_k=int(fusion_raw.get("rrf_k", 0)),
            weights={name: float(weights_raw[name]) for name in MODEL_NAMES},
        ),
        split=SplitConfig(
            minimum_gallery=int(split_raw.get("minimum_gallery", 0)),
            maximum_gallery=int(split_raw.get("maximum_gallery", 0)),
            calibration_per_class=int(split_raw.get("calibration_per_class", 0)),
            test_per_class=int(split_raw.get("test_per_class", 0)),
        ),
        calibration=CalibrationConfig(
            maximum_ood_false_acceptance=float(
                calibration_raw.get("maximum_ood_false_acceptance", -1)
            ),
            minimum_winner_models=int(calibration_raw.get("minimum_winner_models", 0)),
            calibration_negative_count=int(calibration_raw.get("calibration_negative_count", 0)),
            test_negative_count=int(calibration_raw.get("test_negative_count", 0)),
        ),
        evaluation=EvaluationConfig(
            independent_positive_count=int(evaluation_raw.get("independent_positive_count", 0))
        ),
    )
    if config.schema_version != 1:
        raise ConfigurationError("unsupported ML config schema")
    if config.index.kind != "IndexFlatIP" or config.index.aggregation_top_n != 3:
        raise ConfigurationError("only mean-top-three IndexFlatIP artifacts are supported")
    if not config.index.search_all_gallery:
        raise ConfigurationError("index search must cover the complete gallery")
    if config.fusion.method != "reciprocal_rank" or config.fusion.rrf_k != 60:
        raise ConfigurationError("the frozen fusion contract requires equal RRF with k=60")
    if any(weight != 1.0 for weight in config.fusion.weights.values()):
        raise ConfigurationError("the frozen fusion contract requires unit weights")
    if config.split != SplitConfig(8, 20, 2, 2):
        raise ConfigurationError("split quotas differ from the frozen curation contract")
    if config.calibration != CalibrationConfig(0.05, 2, 50, 50):
        raise ConfigurationError("calibration settings differ from the frozen rejection contract")
    if config.evaluation != EvaluationConfig(20):
        raise ConfigurationError("evaluation counts differ from the frozen contract")
    load_canonical_monument_ids(config.paths.canonical_monuments)
    return config
