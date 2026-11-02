"""Startup-loaded, concurrency-safe monument recognition service."""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from pathlib import Path

from PIL import Image

from raahein_ml.calibration import (
    FusionGate,
    SingleModelGate,
    fusion_accept,
    gates_from_metadata,
    single_accept,
)
from raahein_ml.config import MODEL_NAMES, MLConfig, ModelSpec, load_config
from raahein_ml.encoders import Encoder, create_encoder
from raahein_ml.fusion import ranking_positions, reciprocal_rank_fusion
from raahein_ml.indexes import ArtifactBundle, load_artifact
from raahein_ml.schemas import (
    Candidate,
    ConfigurationError,
    InferenceError,
    NotReadyError,
    PredictionTrace,
    ReadinessSnapshot,
    RecognitionError,
    RecognitionResult,
    ServiceState,
)

EncoderFactory = Callable[[ModelSpec, MLConfig], Encoder]
ArtifactLoader = Callable[[Path, MLConfig], ArtifactBundle]


def _default_encoder_factory(spec: ModelSpec, config: MLConfig) -> Encoder:
    return create_encoder(spec, config)


def _default_artifact_loader(path: Path, config: MLConfig) -> ArtifactBundle:
    return load_artifact(path, config)


def resolve_artifact_path(configured: Path) -> Path:
    configured = configured.resolve()
    if (configured / "metadata.json").is_file():
        return configured
    current = configured / "current"
    if (current / "metadata.json").is_file():
        return current
    if not configured.is_dir():
        raise ConfigurationError(f"recognition artifact directory does not exist: {configured}")
    candidates = sorted(
        child
        for child in configured.iterdir()
        if child.is_dir() and (child / "metadata.json").is_file()
    )
    if len(candidates) != 1:
        raise ConfigurationError(
            "artifact root must contain exactly one artifact or an explicit current artifact"
        )
    return candidates[0]


class RecognitionService:
    """Owns one process-local set of encoders and immutable CPU indexes."""

    def __init__(
        self,
        config: MLConfig,
        *,
        artifact_path: Path | None = None,
        encoder_factory: EncoderFactory = _default_encoder_factory,
        artifact_loader: ArtifactLoader = _default_artifact_loader,
    ) -> None:
        self.config = config
        self._artifact_path = artifact_path
        self._encoder_factory = encoder_factory
        self._artifact_loader = artifact_loader
        self._condition = threading.Condition(threading.RLock())
        self._inference_lock = threading.Lock()
        self._state: ServiceState = "new"
        self._error: str | None = None
        self._bundle: ArtifactBundle | None = None
        self._encoders: Mapping[str, Encoder] = {}
        self._single_gates: Mapping[str, SingleModelGate] = {}
        self._fusion_gate: FusionGate | None = None

    def start(self) -> None:
        with self._condition:
            while self._state == "starting":
                self._condition.wait()
            if self._state == "ready":
                return
            if self._state == "failed":
                raise ConfigurationError(self._error or "recognition startup previously failed")
            self._state = "starting"
            self._error = None

        try:
            artifact_path = self._artifact_path or resolve_artifact_path(
                self.config.paths.artifacts
            )
            bundle = self._artifact_loader(artifact_path, self.config)
            single_gates, fusion_gate = gates_from_metadata(bundle.gates)
            encoders: dict[str, Encoder] = {}
            for name in MODEL_NAMES:
                encoder = self._encoder_factory(self.config.models[name], self.config)
                encoder.load()
                encoder.warmup()
                encoders[name] = encoder
        except BaseException as exc:
            with self._condition:
                self._state = "failed"
                self._error = str(exc) or type(exc).__name__
                self._condition.notify_all()
            if isinstance(exc, RecognitionError):
                raise
            if isinstance(exc, Exception):
                raise ConfigurationError("recognition service startup failed") from exc
            raise

        with self._condition:
            self._bundle = bundle
            self._encoders = encoders
            self._single_gates = single_gates
            self._fusion_gate = fusion_gate
            self._state = "ready"
            self._condition.notify_all()

    @property
    def readiness(self) -> ReadinessSnapshot:
        with self._condition:
            artifact_version = self._bundle.artifact_id if self._bundle else None
            return ReadinessSnapshot(
                state=self._state,
                ready=self._state == "ready",
                artifact_version=artifact_version,
                device=self.config.device,
                models_loaded=tuple(self._encoders),
                error=self._error,
            )

    def _ready_components(
        self,
    ) -> tuple[
        ArtifactBundle,
        Mapping[str, Encoder],
        Mapping[str, SingleModelGate],
        FusionGate,
    ]:
        with self._condition:
            if self._state != "ready" or self._bundle is None or self._fusion_gate is None:
                detail = f": {self._error}" if self._error else ""
                raise NotReadyError(f"recognition service is {self._state}{detail}")
            return self._bundle, self._encoders, self._single_gates, self._fusion_gate

    def predict_trace(self, image: Image.Image) -> PredictionTrace:
        bundle, encoders, _, _ = self._ready_components()
        try:
            vectors = {}
            with self._inference_lock:
                for name in MODEL_NAMES:
                    vectors[name] = encoders[name].encode([image])[0]
            rankings = {
                name: bundle.indexes[name].search(vectors[name]) for name in MODEL_NAMES
            }
            fused = reciprocal_rank_fusion(
                rankings,
                rrf_k=self.config.fusion.rrf_k,
                weights=self.config.fusion.weights,
            )
            return PredictionTrace(model_rankings=rankings, fusion_ranking=fused)
        except RecognitionError:
            raise
        except Exception as exc:
            raise InferenceError("monument recognition inference failed") from exc

    def identify(self, image: Image.Image) -> RecognitionResult:
        bundle, _, _, _ = self._ready_components()
        trace = self.predict_trace(image)
        strategy = bundle.active_strategy
        accepted = self.accepts(trace, strategy)
        ranking = trace.ranking(strategy)
        fused_scores = {item.monument_id: item.score for item in trace.fusion_ranking}
        model_positions = {
            name: ranking_positions(model_ranking)
            for name, model_ranking in trace.model_rankings.items()
        }
        candidates = tuple(
            Candidate(
                monument_id=item.monument_id,
                rank=rank,
                ranking_score=item.score,
                fused_score=fused_scores.get(item.monument_id),
                model_ranks={
                    name: positions[item.monument_id]
                    for name, positions in model_positions.items()
                },
            )
            for rank, item in enumerate(ranking[:3], start=1)
        )
        return RecognitionResult(
            status="identified" if accepted else "uncertain",
            strategy=strategy,
            candidates=candidates,
            artifact_version=bundle.artifact_id,
        )

    def accepts(self, trace: PredictionTrace, strategy: str) -> bool:
        _, _, single_gates, fusion_gate = self._ready_components()
        if strategy == "fusion":
            return fusion_accept(trace, fusion_gate)
        try:
            return single_accept(trace, strategy, single_gates[strategy])
        except KeyError as exc:
            raise ConfigurationError(f"artifact has no gate for {strategy}") from exc


_singleton_lock = threading.Lock()
_singleton: RecognitionService | None = None
_singleton_signature: tuple[Path, Path | None] | None = None


def get_recognition_service(
    config_path: str | Path | None = None,
    *,
    artifact_path: Path | None = None,
    start: bool = True,
) -> RecognitionService:
    global _singleton, _singleton_signature
    config = load_config(config_path)
    signature = (
        config.config_path,
        None if artifact_path is None else artifact_path.resolve(),
    )
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = RecognitionService(config, artifact_path=artifact_path)
                _singleton_signature = signature
    if _singleton_signature != signature:
        raise ConfigurationError("recognition singleton is already configured for another artifact")
    service = _singleton
    if service is None:  # pragma: no cover - defensive for static type narrowing
        raise ConfigurationError("recognition singleton initialization failed")
    if start:
        service.start()
    return service


def _reset_singleton_for_tests() -> None:
    global _singleton, _singleton_signature
    with _singleton_lock:
        _singleton = None
        _singleton_signature = None
