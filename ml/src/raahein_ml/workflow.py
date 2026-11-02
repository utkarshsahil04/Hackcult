"""GPU preparation workflows kept separate from request-time service code."""

from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path, PurePosixPath

import numpy as np
from PIL import Image

from raahein_ml.cache import EmbeddingCache
from raahein_ml.calibration import LabeledTrace, calibrate
from raahein_ml.config import (
    MODEL_NAMES,
    MLConfig,
    semantic_csv_hash,
    semantic_hash,
)
from raahein_ml.dedupe import phash_hamming_distance
from raahein_ml.encoders import Encoder, create_encoder
from raahein_ml.evaluate import OOD_CATEGORIES
from raahein_ml.fusion import reciprocal_rank_fusion
from raahein_ml.indexes import (
    ArtifactBundle,
    MappingRow,
    build_staged_artifact,
    finalize_artifact,
    load_artifact,
)
from raahein_ml.manifest import (
    ALLOWED_LICENSES,
    NEGATIVE_FIELDS,
    ManifestError,
    ManifestRow,
    analyze_image,
    read_manifest,
    validate_manifests,
    validate_provenance_url,
)
from raahein_ml.schemas import ArtifactError, PredictionTrace


@dataclass(frozen=True, slots=True)
class NegativeRow:
    image_id: str
    category: str
    local_path: str
    source_id: str
    source_page_url: str
    download_url: str
    license_id: str
    sha256: str
    phash: str


def _image_path(config: MLConfig, local_path: str) -> Path:
    pure = PurePosixPath(local_path)
    if pure.is_absolute() or ".." in pure.parts:
        raise ArtifactError(f"unsafe local image path: {local_path}")
    resolved = (config.repository_root / Path(*pure.parts)).resolve()
    try:
        resolved.relative_to(config.repository_root)
    except ValueError as exc:
        raise ArtifactError(f"local image path escapes repository: {local_path}") from exc
    return resolved


def _encode_path(encoder: Encoder, path: Path) -> np.ndarray:
    try:
        with Image.open(path) as image:
            image.load()
            return encoder.encode([image])[0]
    except OSError as exc:
        raise ArtifactError(f"cannot decode image for embedding: {path}") from exc


def build_gallery_indexes(config: MLConfig, staging_dir: Path | None = None) -> Path:
    manifest_rows = list(read_manifest(config.paths.manifest))
    independent_rows = list(
        read_manifest(config.paths.manifest.parent / "independent_test.csv")
    )
    validate_manifests(
        manifest_rows,
        independent_rows,
        config,
        rehash=True,
        require_independent_count=True,
    )
    gallery = sorted(
        [row for row in manifest_rows if row.status == "accepted" and row.split == "gallery"],
        key=lambda row: row.image_id,
    )
    mapping = [
        MappingRow(
            row=index,
            image_id=row.image_id,
            monument_id=row.monument_id,
            image_sha256=row.sha256,
        )
        for index, row in enumerate(gallery)
    ]
    cache = EmbeddingCache(config.paths.embedding_cache)
    embeddings: dict[str, np.ndarray] = {}
    extraction_configs: dict[str, dict[str, object]] = {}
    for name in MODEL_NAMES:
        encoder = create_encoder(config.models[name], config)
        encoder.load()
        encoder.warmup()
        extraction_configs[name] = encoder.extraction_config
        vectors = []
        for row in gallery:
            path = _image_path(config, row.local_path)
            vector = cache.get_or_compute(
                image_sha256=row.sha256,
                spec=config.models[name],
                extraction=encoder.extraction_config,
                compute=lambda encoder=encoder, path=path: _encode_path(encoder, path),
            )
            vectors.append(vector)
        embeddings[name] = np.stack(vectors).astype(np.float32, copy=False)

    destination = staging_dir or config.paths.artifacts / ".staging"
    return build_staged_artifact(
        destination,
        mapping=mapping,
        embeddings=embeddings,
        config=config,
        manifest_hash=semantic_csv_hash(config.paths.manifest),
        catalog_hash=semantic_csv_hash(config.paths.source_catalog),
        extraction_configs=extraction_configs,
    )


def _read_negative_rows(path: Path, config: MLConfig) -> tuple[NegativeRow, ...]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != NEGATIVE_FIELDS:
                raise ArtifactError(f"{path} has an unexpected negative-manifest header")
            raw_rows = [dict(row) for row in reader]
    except OSError as exc:
        raise ArtifactError(f"cannot read negative manifest: {path}") from exc
    rows: list[NegativeRow] = []
    for raw in raw_rows:
        required = (
            "image_id",
            "category",
            "local_path",
            "source_id",
            "source_page_url",
            "download_url",
            "author",
            "license_id",
            "license_url",
            "attribution",
            "sha256",
            "phash",
        )
        if any(not (raw[field] or "").strip() for field in required):
            raise ArtifactError("negative manifest has incomplete provenance")
        row = NegativeRow(
            image_id=raw["image_id"].strip(),
            category=raw["category"].strip(),
            local_path=raw["local_path"].strip(),
            source_id=raw["source_id"].strip(),
            source_page_url=raw["source_page_url"].strip(),
            download_url=raw["download_url"].strip(),
            license_id=raw["license_id"].strip(),
            sha256=raw["sha256"].strip(),
            phash=raw["phash"].strip(),
        )
        if row.license_id not in ALLOWED_LICENSES:
            raise ArtifactError(f"negative {row.image_id} has a disallowed licence")
        if row.category not in OOD_CATEGORIES:
            raise ArtifactError(f"negative {row.image_id} has an invalid category")
        for field in ("source_page_url", "download_url", "license_url"):
            try:
                validate_provenance_url(raw[field].strip(), field)
            except ManifestError as exc:
                raise ArtifactError(f"negative {row.image_id} has invalid {field}") from exc
        analysis = analyze_image(_image_path(config, row.local_path))
        if (row.sha256, row.phash) != (analysis.sha256, analysis.phash):
            raise ArtifactError(f"negative fingerprint differs for {row.image_id}")
        rows.append(row)
    if len({row.image_id.casefold() for row in rows}) != len(rows):
        raise ArtifactError("negative image IDs must be unique")
    return tuple(sorted(rows, key=lambda row: row.image_id))


def _negative_overlap(left: NegativeRow, right: NegativeRow) -> bool:
    return (
        left.sha256 == right.sha256
        or phash_hamming_distance(left.phash, right.phash) <= 4
        or left.source_id == right.source_id
        or left.source_page_url == right.source_page_url
        or left.download_url == right.download_url
        or left.local_path == right.local_path
    )


def _validate_negative_disjointness(
    calibration_rows: tuple[NegativeRow, ...],
    final_rows: tuple[NegativeRow, ...],
    positive_rows: Sequence[ManifestRow],
) -> None:
    for group_name, rows in (
        ("calibration OOD", calibration_rows),
        ("final OOD", final_rows),
    ):
        for left, right in combinations(rows, 2):
            if _negative_overlap(left, right):
                raise ArtifactError(
                    f"{group_name} rows overlap: {left.image_id}/{right.image_id}"
                )
    for calibration in calibration_rows:
        for final in final_rows:
            if _negative_overlap(calibration, final):
                raise ArtifactError(
                    f"calibration/final OOD overlap: {calibration.image_id}/{final.image_id}"
                )
    for negative in (*calibration_rows, *final_rows):
        for positive in positive_rows:
            if positive.status != "accepted":
                continue
            if (
                negative.sha256 == positive.sha256
                or phash_hamming_distance(negative.phash, positive.phash) <= 4
                or negative.source_id == positive.source_id
                or negative.source_page_url == positive.source_page_url
                or negative.download_url == positive.download_url
                or negative.local_path == positive.local_path
            ):
                raise ArtifactError(
                    f"negative {negative.image_id} overlaps positive {positive.image_id}"
                )


def _load_encoders(config: MLConfig) -> dict[str, Encoder]:
    encoders: dict[str, Encoder] = {}
    for name in MODEL_NAMES:
        encoder = create_encoder(config.models[name], config)
        encoder.load()
        encoder.warmup()
        encoders[name] = encoder
    return encoders


def _predict_trace(
    path: Path,
    encoders: dict[str, Encoder],
    artifact: ArtifactBundle,
    config: MLConfig,
) -> PredictionTrace:
    try:
        with Image.open(path) as image:
            image.load()
            vectors = {name: encoders[name].encode([image])[0] for name in MODEL_NAMES}
    except OSError as exc:
        raise ArtifactError(f"cannot decode calibration image: {path}") from exc
    rankings = {
        name: artifact.indexes[name].search(vectors[name]) for name in MODEL_NAMES
    }
    fusion = reciprocal_rank_fusion(
        rankings,
        rrf_k=config.fusion.rrf_k,
        weights=config.fusion.weights,
    )
    return PredictionTrace(model_rankings=rankings, fusion_ranking=fusion)


def calibrate_staged_artifact(
    config: MLConfig,
    staging_dir: Path | None = None,
) -> Path:
    staging = (staging_dir or config.paths.artifacts / ".staging").resolve()
    manifest_rows = list(read_manifest(config.paths.manifest))
    independent_rows = list(
        read_manifest(config.paths.manifest.parent / "independent_test.csv")
    )
    validate_manifests(
        manifest_rows,
        independent_rows,
        config,
        rehash=True,
        require_independent_count=True,
    )
    artifact = load_artifact(staging, config, require_final=False)
    calibration_rows = sorted(
        [
            row
            for row in manifest_rows
            if row.status == "accepted" and row.split == "calibration"
        ],
        key=lambda row: row.image_id,
    )
    counts = Counter(row.monument_id for row in calibration_rows)
    if set(counts) != set(config.canonical_monument_ids) or any(
        counts[slug] != config.split.calibration_per_class
        for slug in config.canonical_monument_ids
    ):
        raise ArtifactError("calibration positives do not meet frozen class counts")
    negative_path = config.paths.manifest.parent / "calibration_negatives.csv"
    negatives = _read_negative_rows(negative_path, config)
    if len(negatives) != config.calibration.calibration_negative_count:
        raise ArtifactError(
            f"calibration requires {config.calibration.calibration_negative_count} negatives"
        )
    category_counts = Counter(row.category for row in negatives)
    expected_category_count = config.calibration.calibration_negative_count // len(
        OOD_CATEGORIES
    )
    if set(category_counts) != set(OOD_CATEGORIES) or any(
        category_counts[category] != expected_category_count for category in OOD_CATEGORIES
    ):
        raise ArtifactError("calibration negatives must be category-balanced")
    final_negative_path = config.paths.manifest.parent / "test_negatives.csv"
    final_negatives = _read_negative_rows(final_negative_path, config)
    if len(final_negatives) != config.calibration.test_negative_count:
        raise ArtifactError(
            f"final evaluation requires {config.calibration.test_negative_count} negatives"
        )
    final_category_counts = Counter(row.category for row in final_negatives)
    if set(final_category_counts) != set(OOD_CATEGORIES) or any(
        final_category_counts[category]
        != config.calibration.test_negative_count // len(OOD_CATEGORIES)
        for category in OOD_CATEGORIES
    ):
        raise ArtifactError("final negatives must be category-balanced")
    _validate_negative_disjointness(
        negatives,
        final_negatives,
        [*manifest_rows, *independent_rows],
    )

    encoders = _load_encoders(config)
    known_traces = [
        LabeledTrace(
            trace=_predict_trace(
                _image_path(config, row.local_path), encoders, artifact, config
            ),
            monument_id=row.monument_id,
        )
        for row in calibration_rows
    ]
    negative_traces = [
        _predict_trace(_image_path(config, row.local_path), encoders, artifact, config)
        for row in negatives
    ]
    result = calibrate(
        known_traces,
        negative_traces,
        maximum_false_acceptance=config.calibration.maximum_ood_false_acceptance,
        minimum_winner_models=config.calibration.minimum_winner_models,
        expected_negative_count=config.calibration.calibration_negative_count,
    )
    calibration_metadata = {
        "positive_count": len(known_traces),
        "negative_count": len(negative_traces),
        "positive_ids_hash": semantic_hash([row.image_id for row in calibration_rows]),
        "negative_manifest_hash": semantic_csv_hash(negative_path),
        "independent_manifest_hash": semantic_csv_hash(
            config.paths.manifest.parent / "independent_test.csv"
        ),
        "test_negative_manifest_hash": semantic_csv_hash(
            final_negative_path
        ),
        "maximum_ood_false_acceptance": config.calibration.maximum_ood_false_acceptance,
        "selection_rule": (
            "fusion_requires_strictly_more_correct_accepts_and_no_selective_accuracy_loss"
        ),
        "results": result.summary_dict(),
    }
    return finalize_artifact(
        staging,
        config.paths.artifacts,
        gates=result.gates_dict(),
        active_strategy=result.active_strategy,
        calibration=calibration_metadata,
    )


def validate_final_artifact(config: MLConfig, artifact_path: Path) -> ArtifactBundle:
    manifest_rows = list(read_manifest(config.paths.manifest))
    independent_rows = list(
        read_manifest(config.paths.manifest.parent / "independent_test.csv")
    )
    validate_manifests(
        manifest_rows,
        independent_rows,
        config,
        rehash=True,
        require_independent_count=True,
    )
    bundle = load_artifact(artifact_path, config)
    if bundle.metadata["manifest_hash"] != semantic_csv_hash(config.paths.manifest):
        raise ArtifactError("artifact manifest hash differs from the tracked manifest")
    if bundle.metadata["catalog_hash"] != semantic_csv_hash(config.paths.source_catalog):
        raise ArtifactError("artifact source-catalog hash differs")
    return bundle
