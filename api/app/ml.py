"""
Recognition pipeline seam.

Wraps raahein_ml.dataset_pipeline (SigLIP + DINOv2 + CLIP, rank fusion, calibrated rejection).
Models load once, on first use or at API startup. Build the artifact first:
    python -m raahein_ml.dataset_pipeline build --dataset <Indian-monuments/images>
"""
from __future__ import annotations

import io
import json
import logging
import threading
from dataclasses import dataclass, field

from PIL import Image, UnidentifiedImageError

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


@dataclass
class PipelineStatus:
    models: str       # "ok" | "not_loaded" | "error"
    faiss_index: str  # "ok" | "not_loaded" | "error"


class RecognitionPipeline:
    def __init__(self) -> None:
        self._recognizer = None
        self._names: dict[str, str] = {}
        self._error: str | None = None
        self._load_lock = threading.Lock()
        self._gpu_lock = threading.Lock()

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
                logger.exception("Recognition pipeline failed to load")
                raise
            self._names = {row["slug"]: row["name"] for row in rows}
            self._recognizer = recognizer
            self._error = None
            logger.info("Recognition pipeline ready (artifact %s)", recognizer.version)

    def status(self) -> PipelineStatus:
        if self._recognizer is not None:
            return PipelineStatus(models="ok", faiss_index="ok")
        state = "error" if self._error else "not_loaded"
        return PipelineStatus(models=state, faiss_index=state)

    def run(self, image_bytes: bytes) -> PipelineResult:
        return self._run(image_bytes)

    def _run(self, image_bytes: bytes) -> PipelineResult:
        if self._recognizer is None:
            self.load()
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
        )


_pipeline: RecognitionPipeline | None = None


def get_pipeline() -> RecognitionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RecognitionPipeline()
    return _pipeline
