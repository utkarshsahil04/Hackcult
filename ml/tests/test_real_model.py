from __future__ import annotations

import os
from pathlib import Path

import pytest
from PIL import Image

from raahein_ml.config import load_config
from raahein_ml.service import RecognitionService


@pytest.mark.real_model
def test_real_model_artifact_smoke() -> None:
    artifact = os.environ.get("RAAHEIN_ML_SMOKE_ARTIFACT")
    image_path = os.environ.get("RAAHEIN_ML_SMOKE_IMAGE")
    if not artifact or not image_path:
        pytest.skip("set RAAHEIN_ML_SMOKE_ARTIFACT and RAAHEIN_ML_SMOKE_IMAGE")
    config = load_config()
    service = RecognitionService(config, artifact_path=Path(artifact))
    service.start()
    with Image.open(image_path) as image:
        image.load()
        result = service.identify(image)
    assert len(result.candidates) == 3
    assert result.artifact_version
