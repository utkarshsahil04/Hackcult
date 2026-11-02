from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from raahein_ml.cache import EmbeddingCache
from raahein_ml.config import MODEL_NAMES, MLConfig
from raahein_ml.fusion import (
    aggregate_monument_scores,
    normalize_vectors,
    reciprocal_rank_fusion,
)
from raahein_ml.indexes import (
    LoadedModelIndex,
    MappingRow,
    build_staged_artifact,
    finalize_artifact,
    load_artifact,
)
from raahein_ml.schemas import ArtifactError, RankedMonument


def _ranking(order: tuple[str, ...], scores: tuple[float, ...]) -> tuple[RankedMonument, ...]:
    return tuple(
        RankedMonument(monument_id=monument_id, rank=rank, score=score)
        for rank, (monument_id, score) in enumerate(zip(order, scores, strict=True), 1)
    )


def test_normalization_rejects_invalid_vectors() -> None:
    normalized = normalize_vectors(np.array([[3.0, 4.0]], dtype=np.float32))
    np.testing.assert_allclose(normalized, [[0.6, 0.8]], atol=1e-6)
    assert normalized.dtype == np.float32
    with pytest.raises(ValueError, match="zero-length"):
        normalize_vectors(np.zeros(3, dtype=np.float32))
    with pytest.raises(ValueError, match="non-finite"):
        normalize_vectors(np.array([np.nan, 1.0], dtype=np.float32))


def test_top_three_aggregation_uses_no_cross_model_scores() -> None:
    ranking = aggregate_monument_scores(
        [0.9, 0.8, 0.7, 0.99, 0.2, 0.1],
        ["a", "a", "a", "b", "b", "b"],
    )
    assert ranking[0].monument_id == "a"
    assert ranking[0].score == pytest.approx(0.8)
    assert ranking[1].score == pytest.approx((0.99 + 0.2 + 0.1) / 3)
    with pytest.raises(ArtifactError, match="3 are required"):
        aggregate_monument_scores([0.9, 0.8], ["a", "a"])


def test_rrf_uses_only_ranks_and_breaks_ties_by_slug() -> None:
    orders = {
        "one": _ranking(("a", "b"), (0.99, -0.5)),
        "two": _ranking(("b", "a"), (0.51, 0.50)),
    }
    changed_raw_scores = {
        "one": _ranking(("a", "b"), (100.0, 99.0)),
        "two": _ranking(("b", "a"), (-10.0, -20.0)),
    }
    first = reciprocal_rank_fusion(orders)
    second = reciprocal_rank_fusion(changed_raw_scores)
    assert first == second
    assert [item.monument_id for item in first] == ["a", "b"]
    assert first[0].score == pytest.approx(first[1].score)


def test_embedding_cache_recomputes_corrupt_entries(
    tmp_path: Path, cpu_config: MLConfig
) -> None:
    cache = EmbeddingCache(tmp_path)
    spec = cpu_config.models["clip"]
    extraction = {"pooling": "get_image_features"}
    calls = 0

    def compute() -> np.ndarray:
        nonlocal calls
        calls += 1
        vector = np.arange(1, spec.dimension + 1, dtype=np.float32)
        return vector

    first = cache.get_or_compute(
        image_sha256="a" * 64,
        spec=spec,
        extraction=extraction,
        compute=compute,
    )
    second = cache.get_or_compute(
        image_sha256="a" * 64,
        spec=spec,
        extraction=extraction,
        compute=compute,
    )
    np.testing.assert_array_equal(first, second)
    assert calls == 1

    key = cache.key("a" * 64, spec, extraction)
    cache.path_for(spec.name, key).write_bytes(b"corrupt")
    cache.get_or_compute(
        image_sha256="a" * 64,
        spec=spec,
        extraction=extraction,
        compute=compute,
    )
    assert calls == 2


class _CapturingIndex:
    d = 2

    def __init__(self, count: int) -> None:
        self.ntotal = count
        self.search_k: int | None = None

    def search(self, query: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        self.search_k = k
        return (
            np.linspace(1.0, 0.0, k, dtype=np.float32).reshape(1, -1),
            np.arange(k, dtype=np.int64).reshape(1, -1),
        )


def test_loaded_index_searches_the_complete_gallery(cpu_config: MLConfig) -> None:
    mapping = tuple(
        MappingRow(
            row=index,
            image_id=f"image-{index}",
            monument_id=cpu_config.canonical_monument_ids[index // 8],
            image_sha256=f"{index:064x}",
        )
        for index in range(15 * 8)
    )
    fake = _CapturingIndex(len(mapping))
    loaded = LoadedModelIndex("fake", fake, mapping, 3)
    ranking = loaded.search(np.array([1.0, 0.0], dtype=np.float32))
    assert fake.search_k == len(mapping)
    assert fake.search_k > 8
    assert len(ranking) == 15


def _artifact_inputs(
    config: MLConfig,
) -> tuple[list[MappingRow], dict[str, np.ndarray]]:
    mapping = [
        MappingRow(
            row=index,
            image_id=f"{slug}-{local_index}",
            monument_id=slug,
            image_sha256=f"{index:064x}",
        )
        for index, (slug, local_index) in enumerate(
            (slug, local_index)
            for slug in config.canonical_monument_ids
            for local_index in range(8)
        )
    ]
    rng = np.random.default_rng(42)
    embeddings = {
        name: normalize_vectors(
            rng.normal(size=(len(mapping), config.models[name].dimension)).astype(np.float32)
        )
        for name in MODEL_NAMES
    }
    return mapping, embeddings


def _gates() -> dict[str, object]:
    return {
        "single": {name: {"threshold": 0.1} for name in MODEL_NAMES},
        "fusion": {
            "model_thresholds": {name: 0.1 for name in MODEL_NAMES},
            "margin_threshold": 0.0,
            "minimum_winner_models": 2,
        },
    }


def test_artifact_round_trip_and_checksum_validation(
    tmp_path: Path, cpu_config: MLConfig
) -> None:
    mapping, embeddings = _artifact_inputs(cpu_config)
    staging = tmp_path / "staging"
    build_staged_artifact(
        staging,
        mapping=mapping,
        embeddings=embeddings,
        config=cpu_config,
        manifest_hash="1" * 64,
        catalog_hash="2" * 64,
    )
    artifact = finalize_artifact(
        staging,
        tmp_path / "artifacts",
        gates=_gates(),
        active_strategy="fusion",
        calibration={"negative_count": 50},
    )
    loaded = load_artifact(artifact, cpu_config, verify_repository_inputs=False)
    assert loaded.artifact_id == artifact.name
    assert tuple(loaded.mapping) == tuple(sorted(mapping, key=lambda row: row.image_id))
    assert set(loaded.indexes) == set(MODEL_NAMES)
    with pytest.raises(ArtifactError, match="manifest hashes differ"):
        load_artifact(artifact, cpu_config)

    index_path = artifact / "clip.faiss"
    index_path.write_bytes(index_path.read_bytes() + b"tamper")
    with pytest.raises(ArtifactError, match="checksum mismatch"):
        load_artifact(artifact, cpu_config, verify_repository_inputs=False)


def test_artifact_model_mismatch_is_rejected(tmp_path: Path, cpu_config: MLConfig) -> None:
    mapping, embeddings = _artifact_inputs(cpu_config)
    staging = tmp_path / "staging"
    build_staged_artifact(
        staging,
        mapping=mapping,
        embeddings=embeddings,
        config=cpu_config,
        manifest_hash="1" * 64,
        catalog_hash="2" * 64,
    )
    metadata_path = staging / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["models"]["clip"]["revision"] = "0" * 40
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ArtifactError, match="model metadata differs"):
        load_artifact(
            staging,
            cpu_config,
            require_final=False,
            verify_repository_inputs=False,
        )
