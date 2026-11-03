"""ML pipeline seam and offline demo cache integration (Issue #17)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.demo_cache import DemoCache

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
    provenance: str = "live_inference"


@dataclass
class PipelineStatus:
    models: str  # "ok" | "not_implemented" | "demo_cache" | "error"
    faiss_index: str  # "ok" | "not_implemented" | "demo_cache" | "error"


class RecognitionPipeline:
    """Recognition pipeline supporting offline demo cache and fallback inference."""

    def __init__(self, demo_cache_path: Path | None = None) -> None:
        self.demo_cache_path = demo_cache_path
        self._demo_cache: DemoCache | None = None

    @property
    def demo_cache(self) -> DemoCache:
        if self._demo_cache is None:
            from app.demo_cache import DemoCache

            self._demo_cache = DemoCache(self.demo_cache_path)
        return self._demo_cache

    def status(self) -> PipelineStatus:
        if self.demo_cache.has_entries():
            return PipelineStatus(models="demo_cache", faiss_index="demo_cache")
        return PipelineStatus(models="not_implemented", faiss_index="not_implemented")

    def run(self, image_bytes: bytes) -> PipelineResult:
        """Entry point for recognition. Checks deterministic demo cache first."""
        cached = self.demo_cache.lookup_bytes(image_bytes)
        if cached is not None:
            return cached
        return self._run(image_bytes)

    def _run(self, image_bytes: bytes) -> PipelineResult:
        # Default fallback when real models are not loaded
        return PipelineResult(
            status="uncertain",
            candidates=[],
            provenance="live_inference",
        )


_pipeline: RecognitionPipeline | None = None


def get_pipeline() -> RecognitionPipeline:
    """Returns the singleton pipeline."""
    global _pipeline
    if _pipeline is None:
        logger.info("Loading recognition pipeline (with demo cache)")
        _pipeline = RecognitionPipeline()
    return _pipeline
