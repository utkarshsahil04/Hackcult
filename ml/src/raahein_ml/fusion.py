"""Pure vector normalization, monument aggregation, and rank fusion."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence

import numpy as np

from raahein_ml.schemas import ArtifactError, RankedMonument


def normalize_vectors(vectors: np.ndarray) -> np.ndarray:
    array = np.asarray(vectors, dtype=np.float32)
    if array.ndim not in {1, 2}:
        raise ValueError("vectors must be one- or two-dimensional")
    if not np.isfinite(array).all():
        raise ValueError("vectors contain non-finite values")
    matrix = array.reshape(1, -1) if array.ndim == 1 else array
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms <= 0):
        raise ValueError("zero-length vectors cannot be normalized")
    normalized = np.ascontiguousarray(matrix / norms, dtype=np.float32)
    return normalized[0] if array.ndim == 1 else normalized


def rank_scores(scores: Mapping[str, float]) -> tuple[RankedMonument, ...]:
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return tuple(
        RankedMonument(monument_id=monument_id, rank=index, score=float(score))
        for index, (monument_id, score) in enumerate(ordered, start=1)
    )


def aggregate_monument_scores(
    similarities: Sequence[float] | np.ndarray,
    row_monuments: Sequence[str],
    *,
    top_n: int = 3,
) -> tuple[RankedMonument, ...]:
    if len(similarities) != len(row_monuments):
        raise ValueError("every similarity requires a mapped monument")
    grouped: dict[str, list[float]] = defaultdict(list)
    for score, monument_id in zip(similarities, row_monuments, strict=True):
        value = float(score)
        if not np.isfinite(value):
            raise ArtifactError("index returned a non-finite similarity")
        grouped[monument_id].append(value)
    scores: dict[str, float] = {}
    for monument_id, values in grouped.items():
        if len(values) < top_n:
            raise ArtifactError(
                f"{monument_id} has {len(values)} references; {top_n} are required"
            )
        scores[monument_id] = float(np.mean(sorted(values, reverse=True)[:top_n]))
    return rank_scores(scores)


def reciprocal_rank_fusion(
    rankings: Mapping[str, Sequence[RankedMonument]],
    *,
    rrf_k: int = 60,
    weights: Mapping[str, float] | None = None,
) -> tuple[RankedMonument, ...]:
    if not rankings:
        raise ValueError("at least one ranking is required")
    if rrf_k <= 0:
        raise ValueError("rrf_k must be positive")
    names = tuple(rankings)
    selected_weights = {name: 1.0 for name in names} if weights is None else dict(weights)
    if set(selected_weights) != set(names):
        raise ValueError("weights must match ranking names")
    if any(weight <= 0 for weight in selected_weights.values()):
        raise ValueError("RRF weights must be positive")

    expected: set[str] | None = None
    rank_maps: dict[str, dict[str, int]] = {}
    for name, ranking in rankings.items():
        monument_ids = [item.monument_id for item in ranking]
        if len(monument_ids) != len(set(monument_ids)):
            raise ValueError(f"{name} ranking contains duplicates")
        current = set(monument_ids)
        if expected is None:
            expected = current
        elif current != expected:
            raise ValueError("all model rankings must cover the same monuments")
        rank_maps[name] = {item.monument_id: index for index, item in enumerate(ranking, 1)}

    maximum = sum(weight / (rrf_k + 1) for weight in selected_weights.values())
    fused: dict[str, float] = {}
    for monument_id in expected or set():
        raw = sum(
            selected_weights[name] / (rrf_k + rank_maps[name][monument_id])
            for name in names
        )
        fused[monument_id] = raw / maximum
    return rank_scores(fused)


def ranking_positions(ranking: Sequence[RankedMonument]) -> dict[str, int]:
    return {item.monument_id: item.rank for item in ranking}
