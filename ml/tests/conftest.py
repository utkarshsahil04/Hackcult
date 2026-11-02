from pathlib import Path

import pytest

from raahein_ml.config import MLConfig, load_config


@pytest.fixture
def cpu_config() -> MLConfig:
    config_path = Path(__file__).parents[1] / "config" / "models.yaml"
    return load_config(
        config_path,
        environ={
            "RAAHEIN_ML_DEVICE": "cpu",
            "RAAHEIN_ML_ALLOW_CPU": "true",
        },
    )
