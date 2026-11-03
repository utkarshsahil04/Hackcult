"""Build, finalize, load, and search validated CPU FAISS artifacts."""

from __future__ import annotations

import importlib.metadata
import json
import os
import shutil
import tempfile
from collections import Counter
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from raahein_ml.config import (
    MODEL_NAMES,
    MLConfig,
    ModelSpec,
    canonical_json_bytes,
    semantic_csv_hash,
    semantic_hash,
    sha256_file,
)
from raahein_ml.encoders import extraction_config
from raahein_ml.fusion import aggregate_monument_scores, normalize_vectors
from raahein_ml.schemas import ArtifactError, RankedMonument

ARTIFACT_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class MappingRow:
    row: int
    image_id: str
    monument_id: str
    image_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "row": self.row,
            "image_id": self.image_id,
            "monument_id": self.monument_id,
            "image_sha256": self.image_sha256,
        }


@dataclass(slots=True)
class LoadedModelIndex:
    name: str
    index: Any
    mapping: tuple[MappingRow, ...]
    top_n: int

    def search(self, vector: np.ndarray) -> tuple[RankedMonument, ...]:
        query = normalize_vectors(np.asarray(vector, dtype=np.float32))
        if query.ndim == 1:
            query = query.reshape(1, -1)
        if query.shape != (1, self.index.d):
            raise ArtifactError(
                f"{self.name} query has shape {query.shape}; expected (1, {self.index.d})"
            )
        search_k = int(self.index.ntotal)
        similarities, indices = self.index.search(np.ascontiguousarray(query), search_k)
        if similarities.shape != (1, search_k) or indices.shape != (1, search_k):
            raise ArtifactError(f"{self.name} index returned an invalid search shape")
        if np.any(indices[0] < 0):
            raise ArtifactError(f"{self.name} index returned an unmapped row")
        try:
            monuments = [self.mapping[int(row)].monument_id for row in indices[0]]
        except (IndexError, ValueError) as exc:
            raise ArtifactError(f"{self.name} index row is outside the common mapping") from exc
        return aggregate_monument_scores(similarities[0], monuments, top_n=self.top_n)


@dataclass(frozen=True, slots=True)
class ArtifactBundle:
    path: Path
    metadata: Mapping[str, Any]
    mapping: tuple[MappingRow, ...]
    indexes: Mapping[str, LoadedModelIndex]

    @property
    def artifact_id(self) -> str:
        return str(self.metadata["artifact_id"])

    @property
    def active_strategy(self) -> str:
        return str(self.metadata["active_strategy"])

    @property
    def gates(self) -> Mapping[str, Any]:
        gates = self.metadata.get("gates")
        if not isinstance(gates, dict):
            raise ArtifactError("artifact gates are missing")
        return gates


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        with suppress(FileNotFoundError):
            os.unlink(temporary_name)
        raise


def _write_json(path: Path, value: object) -> None:
    _atomic_write(path, canonical_json_bytes(value) + b"\n")


def _package_version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _artifact_child(artifact_path: Path, value: object, label: str) -> Path:
    relative = Path(str(value))
    if relative.is_absolute() or len(relative.parts) != 1 or relative.name in {"", ".", ".."}:
        raise ArtifactError(f"artifact {label} path is unsafe")
    return artifact_path / relative


def _verify_checksum(path: Path, expected: object, label: str) -> None:
    try:
        observed = sha256_file(path)
    except OSError as exc:
        raise ArtifactError(f"artifact {label} is missing: {path}") from exc
    if observed != expected:
        raise ArtifactError(f"{label} checksum mismatch")


def _validate_gallery_mapping(
    rows: Sequence[MappingRow], config: MLConfig
) -> tuple[tuple[MappingRow, ...], tuple[int, ...]]:
    indexed = sorted(enumerate(rows), key=lambda item: item[1].image_id)
    order = tuple(index for index, _ in indexed)
    ordered = tuple(row for _, row in indexed)
    if not ordered:
        raise ArtifactError("gallery mapping must not be empty")
    image_ids = [row.image_id for row in ordered]
    if len(image_ids) != len(set(image_ids)):
        raise ArtifactError("gallery image IDs must be unique")
    normalized = tuple(
        MappingRow(
            row=index,
            image_id=row.image_id,
            monument_id=row.monument_id,
            image_sha256=row.image_sha256,
        )
        for index, row in enumerate(ordered)
    )
    counts = Counter(row.monument_id for row in normalized)
    if set(counts) != set(config.canonical_monument_ids):
        raise ArtifactError("gallery must contain every canonical monument and no other label")
    if min(counts.values()) < config.split.minimum_gallery:
        raise ArtifactError("gallery does not meet the configured per-class minimum")
    if len(set(counts.values())) != 1:
        raise ArtifactError("gallery must be class-balanced")
    return normalized, order


def _mapping_payload(mapping: Sequence[MappingRow]) -> bytes:
    return b"".join(canonical_json_bytes(row.to_dict()) + b"\n" for row in mapping)


def build_staged_artifact(
    staging_dir: Path,
    *,
    mapping: Sequence[MappingRow],
    embeddings: Mapping[str, np.ndarray],
    config: MLConfig,
    manifest_hash: str,
    catalog_hash: str,
    extraction_configs: Mapping[str, Mapping[str, object]] | None = None,
) -> Path:
    # Imported here so live recognition skips it: with faiss, SigLIP segfaulted at low memory.
    import faiss

    if staging_dir.exists():
        if any(staging_dir.iterdir()):
            raise ArtifactError(f"staging directory is not empty: {staging_dir}")
    else:
        staging_dir.mkdir(parents=True)
    normalized_mapping, embedding_order = _validate_gallery_mapping(mapping, config)
    mapping_path = staging_dir / "mapping.jsonl"
    _atomic_write(mapping_path, _mapping_payload(normalized_mapping))

    models_metadata: dict[str, object] = {}
    for name in MODEL_NAMES:
        if name not in embeddings:
            raise ArtifactError(f"missing gallery embeddings for {name}")
        spec = config.models[name]
        matrix = normalize_vectors(np.asarray(embeddings[name], dtype=np.float32))
        expected_shape = (len(normalized_mapping), spec.dimension)
        if matrix.shape != expected_shape:
            raise ArtifactError(
                f"{name} embeddings have shape {matrix.shape}; expected {expected_shape}"
            )
        matrix = np.ascontiguousarray(matrix[list(embedding_order)], dtype=np.float32)
        index = faiss.IndexFlatIP(spec.dimension)
        index.add(np.ascontiguousarray(matrix))
        index_path = staging_dir / f"{name}.faiss"
        faiss.write_index(index, str(index_path))
        models_metadata[name] = {
            "model_id": spec.model_id,
            "revision": spec.revision,
            "adapter": spec.adapter,
            "dimension": spec.dimension,
            "preprocessing": dict(spec.preprocessing),
            "processor_hash": spec.processor_hash,
            "extraction": dict(
                extraction_config(spec, config)
                if extraction_configs is None
                else extraction_configs[name]
            ),
            "index_file": index_path.name,
            "index_sha256": sha256_file(index_path),
        }

    class_counts = Counter(row.monument_id for row in normalized_mapping)
    metadata: dict[str, object] = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "state": "built",
        "manifest_hash": manifest_hash,
        "catalog_hash": catalog_hash,
        "config_hash": config.config_hash,
        "canonical_monuments_hash": config.canonical_monuments_hash,
        "canonical_monument_ids": list(config.canonical_monument_ids),
        "models": models_metadata,
        "mapping": {
            "file": mapping_path.name,
            "sha256": sha256_file(mapping_path),
            "count": len(normalized_mapping),
        },
        "gallery_count": len(normalized_mapping),
        "class_counts": dict(sorted(class_counts.items())),
        "index": {
            "kind": "IndexFlatIP",
            "metric": "inner_product",
            "aggregation": "mean_top_3",
            "aggregation_top_n": config.index.aggregation_top_n,
            "search_k": "all_gallery",
        },
        "fusion": {
            "method": "reciprocal_rank",
            "rrf_k": config.fusion.rrf_k,
            "weights": dict(config.fusion.weights),
            "score_normalization": "theoretical_maximum",
        },
        "dependencies": {
            "faiss-cpu": _package_version("faiss-cpu"),
            "numpy": _package_version("numpy"),
            "Pillow": _package_version("Pillow"),
            "torch": _package_version("torch"),
            "transformers": _package_version("transformers"),
        },
    }
    _write_json(staging_dir / "metadata.json", metadata)
    return staging_dir


def finalize_artifact(
    staging_dir: Path,
    artifact_root: Path,
    *,
    gates: Mapping[str, object],
    active_strategy: str,
    calibration: Mapping[str, object],
) -> Path:
    metadata_path = staging_dir / "metadata.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactError("staged metadata is missing or invalid") from exc
    if metadata.get("state") != "built":
        raise ArtifactError("only a built staging artifact can be finalized")
    if active_strategy not in {*MODEL_NAMES, "fusion"}:
        raise ArtifactError(f"invalid active strategy: {active_strategy}")
    finalized = dict(metadata)
    finalized.update(
        {
            "state": "final",
            "gates": dict(gates),
            "active_strategy": active_strategy,
            "calibration": dict(calibration),
        }
    )
    artifact_id = semantic_hash(finalized)
    finalized["artifact_id"] = artifact_id
    _write_json(metadata_path, finalized)

    artifact_root.mkdir(parents=True, exist_ok=True)
    destination = artifact_root / artifact_id
    if destination.exists():
        try:
            existing = json.loads((destination / "metadata.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArtifactError(f"existing artifact is corrupt: {destination}") from exc
        if existing != finalized:
            raise ArtifactError(f"artifact ID collision at {destination}")
        shutil.rmtree(staging_dir)
        return destination
    os.replace(staging_dir, destination)
    return destination


def _read_mapping(path: Path, expected_count: int) -> tuple[MappingRow, ...]:
    rows: list[MappingRow] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                raw = json.loads(line)
                row = MappingRow(
                    row=int(raw["row"]),
                    image_id=str(raw["image_id"]),
                    monument_id=str(raw["monument_id"]),
                    image_sha256=str(raw["image_sha256"]),
                )
                if row.row != line_number - 1:
                    raise ArtifactError("mapping rows are not contiguous")
                rows.append(row)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, ArtifactError):
            raise
        raise ArtifactError(f"cannot read artifact mapping: {path}") from exc
    if len(rows) != expected_count:
        raise ArtifactError(
            f"mapping has {len(rows)} rows; metadata declares {expected_count}"
        )
    if len({row.image_id for row in rows}) != len(rows):
        raise ArtifactError("mapping contains duplicate image IDs")
    return tuple(rows)


def _metadata_mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ArtifactError(f"artifact {name} must be a mapping")
    return value


def _validate_reconstructed_vectors(index: Any, name: str) -> None:
    try:
        vectors = index.reconstruct_n(0, index.ntotal)
    except Exception as exc:
        raise ArtifactError(f"cannot reconstruct {name} vectors for validation") from exc
    norms = np.linalg.norm(np.asarray(vectors, dtype=np.float32), axis=1)
    if not np.allclose(norms, 1.0, atol=1e-4):
        raise ArtifactError(f"{name} index contains non-normalized vectors")


def _verify_repository_inputs(
    metadata: Mapping[str, Any],
    mapping: tuple[MappingRow, ...],
    config: MLConfig,
) -> None:
    try:
        manifest_hash = semantic_csv_hash(config.paths.manifest)
        catalog_hash = semantic_csv_hash(config.paths.source_catalog)
    except (OSError, ValueError) as exc:
        raise ArtifactError("cannot hash current manifest or source catalogue") from exc
    if metadata.get("manifest_hash") != manifest_hash:
        raise ArtifactError("artifact and current manifest hashes differ")
    if metadata.get("catalog_hash") != catalog_hash:
        raise ArtifactError("artifact and current source-catalog hashes differ")
    try:
        from raahein_ml.manifest import read_manifest

        rows = read_manifest(config.paths.manifest)
    except (OSError, ValueError) as exc:
        raise ArtifactError("cannot validate the artifact against the current manifest") from exc
    gallery = sorted(
        [row for row in rows if row.status == "accepted" and row.split == "gallery"],
        key=lambda row: row.image_id,
    )
    expected = tuple(
        (row.image_id, row.monument_id, row.sha256) for row in gallery
    )
    observed = tuple(
        (row.image_id, row.monument_id, row.image_sha256) for row in mapping
    )
    if observed != expected:
        raise ArtifactError("artifact mapping differs from the current gallery manifest")


def load_artifact(
    path: Path,
    config: MLConfig,
    *,
    require_final: bool = True,
    verify_repository_inputs: bool = True,
) -> ArtifactBundle:
    # Imported here so live recognition skips it: with faiss, SigLIP segfaulted at low memory.
    import faiss

    artifact_path = path.resolve()
    metadata_path = artifact_path / "metadata.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"artifact metadata is missing or invalid: {metadata_path}") from exc
    if metadata.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        raise ArtifactError("unsupported artifact schema")
    if require_final and metadata.get("state") != "final":
        raise ArtifactError("recognition requires a finalized artifact")
    if metadata.get("config_hash") != config.config_hash:
        raise ArtifactError("artifact and model configuration hashes differ")
    if metadata.get("canonical_monuments_hash") != config.canonical_monuments_hash:
        raise ArtifactError("artifact and canonical monument catalog hashes differ")
    if tuple(metadata.get("canonical_monument_ids", ())) != config.canonical_monument_ids:
        raise ArtifactError("artifact canonical monument IDs differ")
    if require_final:
        expected_id = metadata.get("artifact_id")
        content = dict(metadata)
        content.pop("artifact_id", None)
        if expected_id != semantic_hash(content):
            raise ArtifactError("artifact ID does not match finalized metadata")

    mapping_metadata = _metadata_mapping(metadata.get("mapping"), "mapping")
    mapping_path = _artifact_child(artifact_path, mapping_metadata.get("file"), "mapping")
    _verify_checksum(mapping_path, mapping_metadata.get("sha256"), "mapping")
    try:
        expected_mapping_count = int(mapping_metadata.get("count", -1))
    except (TypeError, ValueError) as exc:
        raise ArtifactError("artifact mapping count is invalid") from exc
    mapping = _read_mapping(mapping_path, expected_mapping_count)
    if len(mapping) != int(metadata.get("gallery_count", -1)):
        raise ArtifactError("gallery count does not match mapping")
    counts = Counter(row.monument_id for row in mapping)
    if set(counts) != set(config.canonical_monument_ids):
        raise ArtifactError("mapping does not cover the exact canonical label set")
    if min(counts.values()) < config.split.minimum_gallery:
        raise ArtifactError("mapping is below the gallery minimum")
    if len(mapping) <= max(counts.values()):
        raise ArtifactError("full-gallery search k must exceed every per-class count")
    declared_counts = {key: int(value) for key, value in metadata["class_counts"].items()}
    if dict(sorted(counts.items())) != declared_counts:
        raise ArtifactError("class counts do not match mapping")
    if verify_repository_inputs:
        _verify_repository_inputs(metadata, mapping, config)

    models_metadata = _metadata_mapping(metadata.get("models"), "models")
    if set(models_metadata) != set(MODEL_NAMES):
        raise ArtifactError("artifact must contain exactly three configured indexes")
    index_metadata = _metadata_mapping(metadata.get("index"), "index")
    if (
        index_metadata.get("kind") != "IndexFlatIP"
        or index_metadata.get("metric") != "inner_product"
        or int(index_metadata.get("aggregation_top_n", 0)) != config.index.aggregation_top_n
        or index_metadata.get("search_k") != "all_gallery"
    ):
        raise ArtifactError("artifact index configuration differs")

    loaded: dict[str, LoadedModelIndex] = {}
    for name in MODEL_NAMES:
        spec: ModelSpec = config.models[name]
        model_metadata = _metadata_mapping(models_metadata[name], f"models.{name}")
        expected_model_fields = {
            "model_id": spec.model_id,
            "revision": spec.revision,
            "adapter": spec.adapter,
            "dimension": spec.dimension,
            "processor_hash": spec.processor_hash,
            "extraction": extraction_config(spec, config),
        }
        if any(model_metadata.get(key) != value for key, value in expected_model_fields.items()):
            raise ArtifactError(f"{name} artifact model metadata differs from configuration")
        index_path = _artifact_child(
            artifact_path, model_metadata.get("index_file"), f"{name} index"
        )
        _verify_checksum(index_path, model_metadata.get("index_sha256"), f"{name} index")
        try:
            index = faiss.read_index(str(index_path))
        except Exception as exc:
            raise ArtifactError(f"cannot load {name} FAISS index") from exc
        if type(index).__name__ != "IndexFlatIP":
            raise ArtifactError(f"{name} index is not an exact IndexFlatIP")
        if index.metric_type != faiss.METRIC_INNER_PRODUCT:
            raise ArtifactError(f"{name} index does not use inner product")
        if not index.is_trained or index.d != spec.dimension or index.ntotal != len(mapping):
            raise ArtifactError(f"{name} index dimensions or row count differ")
        _validate_reconstructed_vectors(index, name)
        loaded[name] = LoadedModelIndex(
            name=name,
            index=index,
            mapping=mapping,
            top_n=config.index.aggregation_top_n,
        )
    return ArtifactBundle(
        path=artifact_path,
        metadata=metadata,
        mapping=mapping,
        indexes=loaded,
    )
