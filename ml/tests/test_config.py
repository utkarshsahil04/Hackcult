from pathlib import Path

import pytest

from raahein_ml.config import MODEL_NAMES, _require_bool, load_config
from raahein_ml.schemas import ConfigurationError


def test_config_loads_canonical_slugs_and_immutable_revisions() -> None:
    path = Path(__file__).parents[1] / "config" / "models.yaml"
    config = load_config(path)
    assert len(config.canonical_monument_ids) == 15
    assert "taj-mahal" in config.canonical_monument_ids
    assert tuple(config.models) == MODEL_NAMES
    assert all(len(spec.revision) == 40 for spec in config.models.values())


def test_cpu_requires_explicit_development_permission() -> None:
    path = Path(__file__).parents[1] / "config" / "models.yaml"
    with pytest.raises(ConfigurationError, match="explicit"):
        load_config(path, environ={"RAAHEIN_ML_DEVICE": "cpu"})
    config = load_config(
        path,
        environ={"RAAHEIN_ML_DEVICE": "cpu", "RAAHEIN_ML_ALLOW_CPU": "true"},
    )
    assert config.device == "cpu"


def test_yaml_boolean_strings_are_not_truthy_configuration() -> None:
    with pytest.raises(ConfigurationError, match="YAML boolean"):
        _require_bool("false", "field")
