"""Lazy Hugging Face adapters for the frozen vision checkpoints."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

import numpy as np
from PIL import Image

from raahein_ml.config import MLConfig, ModelSpec
from raahein_ml.fusion import normalize_vectors
from raahein_ml.images import prepare_rgb_image
from raahein_ml.schemas import ConfigurationError, InferenceError

ADAPTER_SCHEMA_VERSION = 2


def extraction_config(spec: ModelSpec, config: MLConfig) -> dict[str, object]:
    pooling = "cls_token" if spec.adapter == "dinov2" else "get_image_features"
    return {
        "adapter_schema_version": ADAPTER_SCHEMA_VERSION,
        "pooling": pooling,
        "mixed_precision": config.mixed_precision,
        "device_type": config.device.split(":", maxsplit=1)[0],
        "processor_hash": spec.processor_hash,
    }


class Encoder(Protocol):
    name: str
    spec: ModelSpec

    @property
    def extraction_config(self) -> dict[str, object]: ...

    def load(self) -> None: ...

    def warmup(self) -> None: ...

    def encode(self, images: Sequence[Image.Image]) -> np.ndarray: ...


class HuggingFaceEncoder:
    def __init__(
        self,
        spec: ModelSpec,
        *,
        device: str,
        mixed_precision: bool,
        local_files_only: bool = True,
    ) -> None:
        self.name = spec.name
        self.spec = spec
        self.device = device
        self.mixed_precision = mixed_precision
        self.local_files_only = local_files_only
        self._torch: Any = None
        self._processor: Any = None
        self._model: Any = None

    @property
    def extraction_config(self) -> dict[str, object]:
        return {
            "adapter_schema_version": ADAPTER_SCHEMA_VERSION,
            "pooling": "cls_token" if self.spec.adapter == "dinov2" else "get_image_features",
            "mixed_precision": self.mixed_precision,
            "device_type": self.device.split(":", maxsplit=1)[0],
            "processor_hash": self.spec.processor_hash,
        }

    def load(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoImageProcessor, AutoModel, AutoProcessor
        except ImportError as exc:
            raise ConfigurationError(
                "GPU runtime dependencies are missing; install ml/requirements.txt"
            ) from exc
        if self.device.startswith("cuda") and not torch.cuda.is_available():
            raise ConfigurationError("CUDA is configured but unavailable; CPU fallback is disabled")
        processor_class = AutoImageProcessor if self.spec.adapter == "dinov2" else AutoProcessor
        try:
            processor = processor_class.from_pretrained(
                self.spec.model_id,
                revision=self.spec.revision,
                local_files_only=self.local_files_only,
            )
            model = AutoModel.from_pretrained(
                self.spec.model_id,
                revision=self.spec.revision,
                local_files_only=self.local_files_only,
            )
            model.eval()
            model.to(self.device)
        except Exception as exc:
            raise ConfigurationError(
                f"failed to load frozen {self.name} checkpoint {self.spec.revision}"
            ) from exc
        self._torch = torch
        self._processor = processor
        self._model = model

    @staticmethod
    def _prepare_image(image: Image.Image) -> Image.Image:
        return prepare_rgb_image(image)

    def encode(self, images: Sequence[Image.Image]) -> np.ndarray:
        if not images:
            raise ValueError("at least one image is required")
        if self._model is None:
            raise InferenceError(f"{self.name} is not loaded")
        prepared = [self._prepare_image(image) for image in images]
        try:
            inputs = self._processor(images=prepared, return_tensors="pt")
            inputs = {name: value.to(self.device) for name, value in inputs.items()}
            device_type = self.device.split(":", maxsplit=1)[0]
            autocast_enabled = self.mixed_precision and device_type == "cuda"
            with self._torch.inference_mode(), self._torch.autocast(
                device_type=device_type,
                dtype=self._torch.float16,
                enabled=autocast_enabled,
            ):
                if self.spec.adapter == "dinov2":
                    output = self._model(**inputs).last_hidden_state[:, 0, :]
                else:
                    output = self._model.get_image_features(**inputs)
            vectors = output.detach().float().cpu().numpy()
        except Exception as exc:
            raise InferenceError(f"{self.name} image encoding failed") from exc
        if vectors.shape != (len(images), self.spec.dimension):
            raise InferenceError(
                f"{self.name} returned {vectors.shape}; expected "
                f"({len(images)}, {self.spec.dimension})"
            )
        try:
            return normalize_vectors(vectors)
        except ValueError as exc:
            raise InferenceError(f"{self.name} returned an invalid embedding") from exc

    def warmup(self) -> None:
        vector = self.encode([Image.new("RGB", (224, 224), color=(127, 127, 127))])
        if vector.shape != (1, self.spec.dimension):
            raise InferenceError(f"{self.name} warmup dimension mismatch")


def create_encoder(
    spec: ModelSpec,
    config: MLConfig,
    *,
    local_files_only: bool = True,
) -> HuggingFaceEncoder:
    if spec.adapter not in {"siglip", "dinov2", "clip"}:
        raise ConfigurationError(f"unsupported encoder adapter: {spec.adapter}")
    return HuggingFaceEncoder(
        spec,
        device=config.device,
        mixed_precision=config.mixed_precision,
        local_files_only=local_files_only,
    )


def fetch_models(config: MLConfig) -> None:
    for spec in config.models.values():
        encoder = create_encoder(spec, config, local_files_only=False)
        encoder.load()
