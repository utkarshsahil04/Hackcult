"""Content-addressed cache for curated image embeddings."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable, Mapping
from contextlib import suppress
from pathlib import Path

import numpy as np

from raahein_ml.config import ModelSpec, semantic_hash
from raahein_ml.fusion import normalize_vectors

CACHE_SCHEMA_VERSION = 1


class EmbeddingCache:
    def __init__(self, root: Path) -> None:
        self.root = root

    @staticmethod
    def key(
        image_sha256: str,
        spec: ModelSpec,
        extraction: Mapping[str, object],
    ) -> str:
        return semantic_hash(
            {
                "schema_version": CACHE_SCHEMA_VERSION,
                "image_sha256": image_sha256,
                "model_id": spec.model_id,
                "revision": spec.revision,
                "processor_hash": spec.processor_hash,
                "extraction": dict(extraction),
            }
        )

    def path_for(self, model_name: str, key: str) -> Path:
        return self.root / model_name / f"{key}.npy"

    @staticmethod
    def _validated(vector: np.ndarray, dimension: int) -> np.ndarray:
        array = np.asarray(vector)
        if array.dtype != np.float32 or array.shape != (dimension,):
            raise ValueError("cached embedding has the wrong dtype or shape")
        if not np.isfinite(array).all():
            raise ValueError("cached embedding contains non-finite values")
        norm = float(np.linalg.norm(array))
        if not np.isclose(norm, 1.0, atol=1e-4):
            raise ValueError("cached embedding is not unit normalized")
        return np.ascontiguousarray(array)

    def get(self, path: Path, dimension: int) -> np.ndarray | None:
        if not path.is_file():
            return None
        try:
            vector = np.load(path, allow_pickle=False)
            return self._validated(vector, dimension)
        except (OSError, ValueError):
            return None

    def put(self, path: Path, vector: np.ndarray, dimension: int) -> np.ndarray:
        validated = self._validated(normalize_vectors(vector), dimension)
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        try:
            with os.fdopen(descriptor, "wb") as handle:
                np.save(handle, validated, allow_pickle=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
        except BaseException:
            with suppress(FileNotFoundError):
                os.unlink(temporary_name)
            raise
        return validated

    def get_or_compute(
        self,
        *,
        image_sha256: str,
        spec: ModelSpec,
        extraction: Mapping[str, object],
        compute: Callable[[], np.ndarray],
    ) -> np.ndarray:
        key = self.key(image_sha256, spec, extraction)
        path = self.path_for(spec.name, key)
        cached = self.get(path, spec.dimension)
        if cached is not None:
            return cached
        return self.put(path, compute(), spec.dimension)
