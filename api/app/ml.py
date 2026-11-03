"""Recognition pipeline seam and offline demo cache integration (Issue #17 & #20).

Wraps raahein_ml.dataset_pipeline (SigLIP + DINOv2 + CLIP, rank fusion, calibrated rejection)
with deterministic offline demo cache support for reliable demonstrations.
"""

from __future__ import annotations

import io
import json
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, UnidentifiedImageError

if TYPE_CHECKING:
    from app.demo_cache import DemoCache

logger = logging.getLogger("raahein.ml")


class UnreadableImage(ValueError):
    """The upload passed type checks but cannot be decoded as an image."""


@dataclass
class Candidate:
    slug: str
    name: str
    score: float  # ranking score under the active strategy, not a probability


@dataclass
class PipelineResult:
    status: str  # "ok" | "uncertain" | "error"
    candidates: list[Candidate] = field(default_factory=list)
    error: str | None = None
    provenance: str = "live_inference"


@dataclass
class PipelineStatus:
    models: str  # "ok" | "not_loaded" | "demo_cache" | "error"
    faiss_index: str  # "ok" | "not_loaded" | "demo_cache" | "error"


class RecognitionPipeline:
    """Recognition pipeline supporting real ML models and offline demo cache fallback."""

    def __init__(self, demo_cache_path: Path | None = None) -> None:
        self.demo_cache_path = demo_cache_path
        self._demo_cache: DemoCache | None = None
        self._recognizer = None
        self._names: dict[str, str] = {}
        self._error: str | None = None
        self._load_lock = threading.Lock()
        self._gpu_lock = threading.Lock()

    @property
    def demo_cache(self) -> DemoCache:
        if self._demo_cache is None:
            from app.demo_cache import DemoCache

            self._demo_cache = DemoCache(self.demo_cache_path)
        return self._demo_cache

    def load(self) -> None:
        with self._load_lock:
            if self._recognizer is not None:
                return
            try:
                from raahein_ml.config import load_config
                from raahein_ml.dataset_pipeline import DatasetRecognizer

                config = load_config()
                recognizer = DatasetRecognizer(config)
                recognizer.load()
                rows = json.loads(config.paths.canonical_monuments.read_text(encoding="utf-8"))
            except Exception as exc:
                self._error = f"{type(exc).__name__}: {exc}"
                logger.warning("Recognition pipeline models not loaded: %s", exc)
                raise
            self._names = {row["slug"]: row["name"] for row in rows}
            self._recognizer = recognizer
            self._error = None
            logger.info("Recognition pipeline ready (artifact %s)", recognizer.version)

    def status(self) -> PipelineStatus:
        if self._recognizer is not None:
            return PipelineStatus(models="ok", faiss_index="ok")
        if self._error:
            return PipelineStatus(models="error", faiss_index="error")
        if self.demo_cache.has_entries():
            return PipelineStatus(models="demo_cache", faiss_index="demo_cache")
        return PipelineStatus(models="not_loaded", faiss_index="not_loaded")

    def run(self, image_bytes: bytes) -> PipelineResult:
        """Entry point for recognition. Checks deterministic demo cache first."""
        cached = self.demo_cache.lookup_bytes(image_bytes)
        if cached is not None:
            return cached
        return self._run(image_bytes)

    def _run(self, image_bytes: bytes) -> PipelineResult:
        if self._recognizer is None:
            try:
                self.load()
            except Exception:  # noqa: BLE001
                # Default fallback when real models are not loaded or artifact missing
                return PipelineResult(
                    status="uncertain",
                    candidates=[],
                    provenance="live_inference",
                )
        try:
            with Image.open(io.BytesIO(image_bytes)) as opened:
                image = opened.copy()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise UnreadableImage("could not decode the uploaded image") from exc
        with self._gpu_lock:
            found = self._recognizer.identify(image)
        return PipelineResult(
            status="ok" if found.status == "identified" else "uncertain",
            candidates=[
                Candidate(
                    slug=item.monument_id,
                    name=self._names.get(item.monument_id, item.monument_id),
                    score=item.score,
                )
                for item in found.candidates
            ],
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
