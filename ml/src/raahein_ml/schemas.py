"""Typed service contracts and ML-specific failures."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

RecognitionStatus = Literal["identified", "uncertain"]
ServiceState = Literal["new", "starting", "ready", "failed"]


class RecognitionError(RuntimeError):
    """Base class for recognition failures that are not valid uncertainty."""


class ConfigurationError(RecognitionError):
    """The configured runtime cannot satisfy the frozen artifact contract."""


class ArtifactError(RecognitionError):
    """A persisted recognition artifact is missing, corrupt, or incompatible."""


class NotReadyError(RecognitionError):
    """Recognition was requested before the service became ready."""


class InferenceError(RecognitionError):
    """A loaded encoder or index failed while handling a valid request."""


@dataclass(frozen=True, slots=True)
class RankedMonument:
    monument_id: str
    rank: int
    score: float

    def __post_init__(self) -> None:
        if not self.monument_id:
            raise ValueError("monument_id must not be empty")
        if self.rank < 1:
            raise ValueError("rank must be positive")


@dataclass(frozen=True, slots=True)
class Candidate:
    monument_id: str
    rank: int
    ranking_score: float
    fused_score: float | None
    model_ranks: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.monument_id:
            raise ValueError("monument_id must not be empty")
        if self.rank < 1:
            raise ValueError("rank must be positive")

    def to_dict(self) -> dict[str, object]:
        return {
            "monument_id": self.monument_id,
            "rank": self.rank,
            "ranking_score": self.ranking_score,
            "fused_score": self.fused_score,
            "model_ranks": dict(self.model_ranks),
        }


@dataclass(frozen=True, slots=True)
class RecognitionResult:
    status: RecognitionStatus
    strategy: str
    candidates: tuple[Candidate, ...]
    artifact_version: str

    def __post_init__(self) -> None:
        if not 1 <= len(self.candidates) <= 3:
            raise ValueError("recognition results require one to three candidates")
        if tuple(candidate.rank for candidate in self.candidates) != tuple(
            range(1, len(self.candidates) + 1)
        ):
            raise ValueError("candidate ranks must be contiguous")

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "strategy": self.strategy,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "artifact_version": self.artifact_version,
        }


@dataclass(frozen=True, slots=True)
class PredictionTrace:
    """Complete rankings retained for calibration and ranking metrics."""

    model_rankings: Mapping[str, tuple[RankedMonument, ...]]
    fusion_ranking: tuple[RankedMonument, ...]

    def ranking(self, strategy: str) -> tuple[RankedMonument, ...]:
        if strategy == "fusion":
            return self.fusion_ranking
        try:
            return self.model_rankings[strategy]
        except KeyError as exc:
            raise ValueError(f"unknown strategy: {strategy}") from exc


@dataclass(frozen=True, slots=True)
class ReadinessSnapshot:
    state: ServiceState
    ready: bool
    artifact_version: str | None
    device: str
    models_loaded: tuple[str, ...]
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "ready": self.ready,
            "artifact_version": self.artifact_version,
            "device": self.device,
            "models_loaded": list(self.models_loaded),
            "error": self.error,
        }
