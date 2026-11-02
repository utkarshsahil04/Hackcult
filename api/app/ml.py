"""
ML pipeline seam.

UV replaces _load_pipeline() with real SigLIP + DINOv2 + CLIP + FAISS logic.
Everything else in this file stays untouched.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("raahein.ml")


@dataclass
class Candidate:
    slug: str
    name: str
    score: float  # fused rank score, 0.0–1.0


@dataclass
class PipelineResult:
    status: str  # "ok" | "uncertain" | "error"
    candidates: list[Candidate] = field(default_factory=list)
    error: str | None = None


@dataclass
class PipelineStatus:
    models: str       # "ok" | "not_implemented" | "error"
    faiss_index: str  # "ok" | "not_implemented" | "error"


class RecognitionPipeline:
    """
    Stub implementation. UV replaces _run() with real inference.
    Status is reported honestly: not_implemented until real models load.
    """

    def status(self) -> PipelineStatus:
        return PipelineStatus(models="not_implemented", faiss_index="not_implemented")

    def run(self, image_bytes: bytes) -> PipelineResult:
        """
        Entry point for recognition.
        Replace this method body with real inference; keep the return type.
        """
        return self._run(image_bytes)

    def _run(self, image_bytes: bytes) -> PipelineResult:
        # Stub: UV replaces this block only.
        return PipelineResult(status="uncertain", candidates=[])


_pipeline: RecognitionPipeline | None = None


def get_pipeline() -> RecognitionPipeline:
    """
    Returns the singleton pipeline.
    UV can replace RecognitionPipeline with a subclass and re-point this function.
    """
    global _pipeline
    if _pipeline is None:
        logger.info("Loading recognition pipeline (stub)")
        _pipeline = RecognitionPipeline()
    return _pipeline