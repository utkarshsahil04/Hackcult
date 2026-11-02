from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import raahein_ml.service as service_module
from raahein_ml.calibration import (
    FusionGate,
    LabeledTrace,
    calibrate,
    fusion_accept,
)
from raahein_ml.config import MODEL_NAMES, MLConfig, ModelSpec
from raahein_ml.indexes import ArtifactBundle
from raahein_ml.schemas import ArtifactError, PredictionTrace, RankedMonument
from raahein_ml.service import RecognitionService


def _ranking(
    winner: str,
    score: float,
    monuments: tuple[str, ...],
) -> tuple[RankedMonument, ...]:
    order = (winner, *(monument for monument in monuments if monument != winner))
    return tuple(
        RankedMonument(
            monument_id=monument,
            rank=rank,
            score=score if rank == 1 else score - 0.2 - rank / 1000,
        )
        for rank, monument in enumerate(order, 1)
    )


def _trace(
    monuments: tuple[str, ...],
    *,
    winner: str,
    model_score: float,
    fusion_margin: float,
    model_winners: tuple[str, str, str] | None = None,
    model_scores: tuple[float, float, float] | None = None,
) -> PredictionTrace:
    selected = model_winners or (winner, winner, winner)
    scores = model_scores or (model_score, model_score, model_score)
    model_rankings = {
        name: _ranking(model_winner, score, monuments)
        for name, model_winner, score in zip(MODEL_NAMES, selected, scores, strict=True)
    }
    fusion = list(_ranking(winner, 0.9, monuments))
    second = fusion[1]
    fusion[1] = RankedMonument(second.monument_id, second.rank, 0.9 - fusion_margin)
    return PredictionTrace(model_rankings=model_rankings, fusion_ranking=tuple(fusion))


def test_calibration_honors_two_of_fifty_false_acceptance_boundary(
    cpu_config: MLConfig,
) -> None:
    monuments = cpu_config.canonical_monument_ids
    known = [
        LabeledTrace(
            _trace(monuments, winner=monuments[0], model_score=0.9, fusion_margin=0.1),
            monuments[0],
        )
        for _ in range(10)
    ]
    negatives = [
        _trace(
            monuments,
            winner=monuments[1],
            model_score=0.91 if index < 2 else 0.1,
            fusion_margin=0.2 if index < 2 else 0.001,
        )
        for index in range(50)
    ]
    result = calibrate(known, negatives, expected_negative_count=50)
    assert all(count <= 2 for count in result.negative_accepts.values())
    assert all(metrics.correctly_accepted == 10 for metrics in result.known_metrics.values())
    assert result.active_strategy == "siglip"


def test_fusion_gate_requires_two_supporters_and_margin(cpu_config: MLConfig) -> None:
    monuments = cpu_config.canonical_monument_ids
    gate = FusionGate(
        model_thresholds={name: 0.5 for name in MODEL_NAMES},
        margin_threshold=0.05,
        minimum_winner_models=2,
    )
    one_supporter = _trace(
        monuments,
        winner=monuments[0],
        model_score=0.9,
        fusion_margin=0.1,
        model_winners=(monuments[0], monuments[1], monuments[2]),
    )
    assert not fusion_accept(one_supporter, gate)
    low_margin = _trace(
        monuments,
        winner=monuments[0],
        model_score=0.9,
        fusion_margin=0.01,
    )
    assert not fusion_accept(low_margin, gate)
    accepted = _trace(
        monuments,
        winner=monuments[0],
        model_score=0.9,
        fusion_margin=0.1,
    )
    assert fusion_accept(accepted, gate)


def test_joint_fusion_gate_can_succeed_when_single_models_cannot(
    cpu_config: MLConfig,
) -> None:
    monuments = cpu_config.canonical_monument_ids
    known = [
        LabeledTrace(
            _trace(monuments, winner=monuments[0], model_score=0.9, fusion_margin=0.1),
            monuments[0],
        )
        for _ in range(10)
    ]
    negatives = []
    for index in range(50):
        scores = [0.1, 0.1, 0.1]
        if index < 9:
            scores[index // 3] = 0.95
        negatives.append(
            _trace(
                monuments,
                winner=monuments[1],
                model_score=0.1,
                model_scores=tuple(scores),
                fusion_margin=0.1,
            )
        )
    result = calibrate(known, negatives, expected_negative_count=50)
    assert all(result.known_metrics[name].accepted == 0 for name in MODEL_NAMES)
    assert result.known_metrics["fusion"].correctly_accepted == 10
    assert result.negative_accepts["fusion"] <= 2
    assert result.active_strategy == "fusion"


def test_valid_single_model_is_fallback_when_fusion_is_not_viable(
    cpu_config: MLConfig,
) -> None:
    monuments = cpu_config.canonical_monument_ids
    known = [
        LabeledTrace(
            PredictionTrace(
                model_rankings={
                    "siglip": _ranking(monuments[0], 0.9, monuments),
                    "dinov2": _ranking(monuments[1], 0.4, monuments),
                    "clip": _ranking(monuments[2], 0.4, monuments),
                },
                fusion_ranking=_ranking(monuments[3], 0.9, monuments),
            ),
            monuments[0],
        )
        for _ in range(10)
    ]
    negatives = [
        PredictionTrace(
            model_rankings={
                name: _ranking(monuments[index + 4], 0.1, monuments)
                for index, name in enumerate(MODEL_NAMES)
            },
            fusion_ranking=_ranking(monuments[7], 0.9, monuments),
        )
        for _ in range(50)
    ]
    result = calibrate(known, negatives, expected_negative_count=50)
    assert result.known_metrics["siglip"].correctly_accepted == 10
    assert result.known_metrics["fusion"].accepted == 0
    assert result.active_strategy == "siglip"


class _ConcurrencyTracker:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.active = 0
        self.maximum = 0
        self.loads = 0
        self.warmups = 0


class _FakeEncoder:
    def __init__(self, spec: ModelSpec, tracker: _ConcurrencyTracker) -> None:
        self.name = spec.name
        self.spec = spec
        self.tracker = tracker

    @property
    def extraction_config(self) -> dict[str, object]:
        return {}

    def load(self) -> None:
        self.tracker.loads += 1

    def warmup(self) -> None:
        self.tracker.warmups += 1

    def encode(self, images: list[Image.Image]) -> np.ndarray:
        with self.tracker.lock:
            self.tracker.active += 1
            self.tracker.maximum = max(self.tracker.maximum, self.tracker.active)
        time.sleep(0.005)
        with self.tracker.lock:
            self.tracker.active -= 1
        vector = np.ones((len(images), self.spec.dimension), dtype=np.float32)
        return vector / np.linalg.norm(vector, axis=1, keepdims=True)


class _FakeSearchIndex:
    def __init__(self, ranking: tuple[RankedMonument, ...]) -> None:
        self.ranking = ranking

    def search(self, vector: np.ndarray) -> tuple[RankedMonument, ...]:
        return self.ranking


def _bundle(
    config: MLConfig,
    *,
    threshold: float,
) -> ArtifactBundle:
    monuments = config.canonical_monument_ids
    rankings = {
        "siglip": _ranking(monuments[0], 0.9, monuments),
        "dinov2": _ranking(monuments[0], 0.9, monuments),
        "clip": _ranking(monuments[1], 0.9, monuments),
    }
    gates = {
        "single": {name: {"threshold": threshold} for name in MODEL_NAMES},
        "fusion": {
            "model_thresholds": {name: threshold for name in MODEL_NAMES},
            "margin_threshold": 0.0,
            "minimum_winner_models": 2,
        },
    }
    return ArtifactBundle(
        path=Path("artifact"),
        metadata={
            "artifact_id": "artifact-v1",
            "active_strategy": "fusion",
            "gates": gates,
        },
        mapping=(),
        indexes={name: _FakeSearchIndex(ranking) for name, ranking in rankings.items()},
    )


def _service(
    config: MLConfig,
    tracker: _ConcurrencyTracker,
    *,
    threshold: float,
) -> RecognitionService:
    bundle = _bundle(config, threshold=threshold)
    return RecognitionService(
        config,
        artifact_path=Path("unused"),
        encoder_factory=lambda spec, _: _FakeEncoder(spec, tracker),
        artifact_loader=lambda _path, _config: bundle,
    )


def test_service_loads_once_and_returns_candidates_for_uncertainty(
    cpu_config: MLConfig,
) -> None:
    tracker = _ConcurrencyTracker()
    service = _service(cpu_config, tracker, threshold=1.1)
    service.start()
    service.start()
    result = service.identify(Image.new("RGB", (32, 32)))
    assert tracker.loads == 3
    assert tracker.warmups == 3
    assert result.status == "uncertain"
    assert result.strategy == "fusion"
    assert len(result.candidates) == 3
    assert all(candidate.fused_score is not None for candidate in result.candidates)
    assert service.readiness.ready


def test_service_serializes_concurrent_encoder_calls(cpu_config: MLConfig) -> None:
    tracker = _ConcurrencyTracker()
    service = _service(cpu_config, tracker, threshold=0.1)
    service.start()
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(
            executor.map(
                service.identify,
                [Image.new("RGB", (32, 32), (index, index, index)) for index in range(4)],
            )
        )
    assert all(result.status == "identified" for result in results)
    assert tracker.maximum == 1


def test_startup_failure_is_not_returned_as_uncertainty(cpu_config: MLConfig) -> None:
    service = RecognitionService(
        cpu_config,
        artifact_path=Path("missing"),
        artifact_loader=lambda _path, _config: (_ for _ in ()).throw(
            ArtifactError("missing artifact")
        ),
    )
    with pytest.raises(ArtifactError, match="missing artifact"):
        service.start()
    assert service.readiness.state == "failed"
    with pytest.raises(Exception, match="recognition service is failed"):
        service.identify(Image.new("RGB", (32, 32)))


def test_process_singleton_factory_constructs_only_once(
    monkeypatch: pytest.MonkeyPatch, cpu_config: MLConfig
) -> None:
    service_module._reset_singleton_for_tests()
    constructed = 0

    class StubService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            nonlocal constructed
            time.sleep(0.002)
            constructed += 1

    monkeypatch.setattr(service_module, "load_config", lambda _path=None: cpu_config)
    monkeypatch.setattr(service_module, "RecognitionService", StubService)
    with ThreadPoolExecutor(max_workers=8) as executor:
        instances = list(
            executor.map(
                lambda _: service_module.get_recognition_service(start=False),
                range(16),
            )
        )
    assert constructed == 1
    assert all(instance is instances[0] for instance in instances)
    service_module._reset_singleton_for_tests()
