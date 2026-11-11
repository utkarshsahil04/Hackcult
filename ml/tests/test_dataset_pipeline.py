import json

import numpy as np
from PIL import Image

from raahein_ml.calibration import LabeledTrace
from raahein_ml.config import MODEL_NAMES, MLConfig
from raahein_ml.dataset_pipeline import (
    CLASS_TO_SLUG,
    NEGATIVE_CALIBRATION,
    NEGATIVE_TEST,
    DatasetRecognizer,
    _plan_roles,
    _trace,
)


def _write(folder, count):
    folder.mkdir(parents=True)
    for index in range(count):
        Image.new("RGB", (8, 8), (index, 0, 0)).save(folder / f"{index}.jpg")


def test_roles_never_mix_classes_or_leak_test_into_gallery(tmp_path) -> None:
    for split in ("train", "test"):
        for folder in ("tajmahal", "qutub_minar", "iron_pillar"):
            _write(tmp_path / split / folder, 10)
    _write(tmp_path / "train" / "charminar", 4)
    _write(tmp_path / "train" / "Ajanta Caves", 4)
    _write(tmp_path / "test" / "Hawa mahal", 4)

    plan = _plan_roles(tmp_path)
    by_role: dict[str, list[dict]] = {}
    for item in plan:
        by_role.setdefault(item["role"], []).append(item)

    assert {i["path"].parent.parent.name for i in by_role["test"]} == {"test"}
    train_roles = by_role["gallery"] + by_role["calib"]
    assert {i["path"].parent.parent.name for i in train_roles} == {"train"}
    # Qutb components share one canonical identity.
    qutb = {i["slug"] for i in plan if i["key"] in {"qutub_minar", "iron_pillar"}}
    assert qutb == {"qutb-complex"}
    assert {i["key"] for i in by_role["calib_neg"]} <= NEGATIVE_CALIBRATION
    assert {i["key"] for i in by_role["test_neg"]} <= NEGATIVE_TEST
    assert "hawa mahal pics" in {i["key"] for i in by_role["test_neg"]}  # test/ folder alias
    assert NEGATIVE_CALIBRATION.isdisjoint(NEGATIVE_TEST)
    assert NEGATIVE_CALIBRATION.isdisjoint(CLASS_TO_SLUG)


def test_trace_ranks_the_matching_monument_first(cpu_config: MLConfig) -> None:
    rng = np.random.default_rng(0)
    labels = ["a"] * 3 + ["b"] * 3
    gallery, query = {}, {}
    for name in MODEL_NAMES:
        rows = rng.normal(size=(6, 16)).astype(np.float32)
        gallery[name] = rows / np.linalg.norm(rows, axis=1, keepdims=True)
        query[name] = gallery[name][0]
    trace = _trace(query, gallery, labels, cpu_config)
    assert trace.fusion_ranking[0].monument_id == "a"
    assert all(r[0].monument_id == "a" for r in trace.model_rankings.values())


def _artifact(path, strategy: str, models) -> np.ndarray:
    """Tiny artifact whose first row is the photo the fake encoder 'sees'."""
    rng = np.random.default_rng(0)
    rows = rng.normal(size=(6, 16)).astype(np.float32)
    rows /= np.linalg.norm(rows, axis=1, keepdims=True)
    for name in models:
        np.save(path / f"{name}.npy", rows)
    (path / "labels.json").write_text(json.dumps(["a"] * 3 + ["b"] * 3), encoding="utf-8")
    gates = {
        "single": {n: {"threshold": 0.1} for n in MODEL_NAMES},
        "fusion": {
            "model_thresholds": dict.fromkeys(MODEL_NAMES, 0.1),
            "margin_threshold": 0.0,
            "minimum_winner_models": 2,
        },
    }
    meta = {"gates": gates, "active_strategy": strategy}
    (path / "gates.json").write_text(json.dumps(meta), encoding="utf-8")
    return rows[0]


def _recognizer(tmp_path, monkeypatch, config, strategy: str, models):
    query = _artifact(tmp_path, strategy, models)
    loaded = []

    class FakeEncoder:
        def __init__(self, spec, _config):
            loaded.append(spec.adapter)

        def load(self):
            pass

        def warmup(self):
            pass

        def encode(self, _images):
            return np.array([query])

    monkeypatch.setattr("raahein_ml.dataset_pipeline.create_encoder", FakeEncoder)
    recognizer = DatasetRecognizer(config, path=tmp_path)
    recognizer.load()
    return recognizer, loaded


def test_single_strategy_uses_only_the_active_model(tmp_path, monkeypatch, cpu_config) -> None:
    recognizer, loaded = _recognizer(tmp_path, monkeypatch, cpu_config, "dinov2", ["dinov2"])
    found = recognizer.identify(Image.new("RGB", (8, 8)))
    assert loaded == ["dinov2"]
    assert found.status == "identified"
    assert found.candidates[0].monument_id == "a"


def test_fusion_strategy_still_uses_every_model(tmp_path, monkeypatch, cpu_config) -> None:
    recognizer, loaded = _recognizer(tmp_path, monkeypatch, cpu_config, "fusion", MODEL_NAMES)
    found = recognizer.identify(Image.new("RGB", (8, 8)))
    assert len(loaded) == len(MODEL_NAMES)
    assert found.status == "identified"
    assert found.candidates[0].monument_id == "a"


def test_new_targets_are_mapped_and_not_negatives() -> None:
    assert CLASS_TO_SLUG["lotus_temple"] == "lotus-temple"
    assert CLASS_TO_SLUG["india gate pics"] == "india-gate"
    assert not ({"lotus_temple", "india gate pics"} & (NEGATIVE_CALIBRATION | NEGATIVE_TEST))
    assert NEGATIVE_TEST.isdisjoint(CLASS_TO_SLUG)


def test_single_gate_margin_rejects_lookalike_with_high_top1() -> None:
    from raahein_ml.calibration import SingleModelGate, calibrate_single_model, single_accept
    from raahein_ml.schemas import PredictionTrace, RankedMonument

    def trace(a: float, b: float, win: str = "x") -> PredictionTrace:
        other = "y" if win == "x" else "x"
        return PredictionTrace(
            model_rankings={"dinov2": (RankedMonument(win, 1, a), RankedMonument(other, 2, b))},
            fusion_ranking=(),
        )

    known = [LabeledTrace(trace(0.8, 0.3), "x"), LabeledTrace(trace(0.7, 0.2), "x")]
    # A look-alike: top1 as high as the real photos, but the runner-up is close behind.
    negatives = [trace(0.8, 0.75), trace(0.9, 0.85)]
    gate, metrics, fa = calibrate_single_model(
        "dinov2", known, negatives, maximum_false_acceptance=0.0, use_margin=True
    )
    assert fa == 0 and metrics.correctly_accepted == 2 and gate.margin > 0.05
    assert not single_accept(negatives[0], "dinov2", gate)
    assert single_accept(known[0].trace, "dinov2", SingleModelGate(0.5))
