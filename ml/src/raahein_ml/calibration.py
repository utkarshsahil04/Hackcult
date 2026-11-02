"""Deterministic rejection calibration on known and OOD calibration sets."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import product

import numpy as np

from raahein_ml.config import MODEL_NAMES
from raahein_ml.schemas import ArtifactError, PredictionTrace


@dataclass(frozen=True, slots=True)
class LabeledTrace:
    trace: PredictionTrace
    monument_id: str | None


@dataclass(frozen=True, slots=True)
class GateMetrics:
    accepted: int
    correctly_accepted: int
    total: int

    @property
    def coverage(self) -> float:
        return self.accepted / self.total if self.total else 0.0

    @property
    def selective_accuracy(self) -> float:
        return self.correctly_accepted / self.accepted if self.accepted else 0.0


@dataclass(frozen=True, slots=True)
class SingleModelGate:
    threshold: float

    def to_dict(self) -> dict[str, float]:
        return {"threshold": self.threshold}


@dataclass(frozen=True, slots=True)
class FusionGate:
    model_thresholds: Mapping[str, float]
    margin_threshold: float
    minimum_winner_models: int

    def to_dict(self) -> dict[str, object]:
        return {
            "model_thresholds": dict(self.model_thresholds),
            "margin_threshold": self.margin_threshold,
            "minimum_winner_models": self.minimum_winner_models,
        }


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    single_gates: Mapping[str, SingleModelGate]
    fusion_gate: FusionGate
    active_strategy: str
    known_metrics: Mapping[str, GateMetrics]
    negative_accepts: Mapping[str, int]

    def gates_dict(self) -> dict[str, object]:
        return {
            "single": {name: gate.to_dict() for name, gate in self.single_gates.items()},
            "fusion": self.fusion_gate.to_dict(),
        }

    def summary_dict(self) -> dict[str, object]:
        return {
            "known": {
                name: {
                    "accepted": metrics.accepted,
                    "correctly_accepted": metrics.correctly_accepted,
                    "total": metrics.total,
                    "coverage": metrics.coverage,
                    "selective_accuracy": metrics.selective_accuracy,
                }
                for name, metrics in self.known_metrics.items()
            },
            "negative_accepts": dict(self.negative_accepts),
        }


def _candidate_thresholds(values: Sequence[float]) -> tuple[float, ...]:
    if not values:
        raise ArtifactError("calibration requires observed scores")
    finite = sorted({float(value) for value in values if np.isfinite(value)})
    if not finite:
        raise ArtifactError("calibration scores are not finite")
    candidates = {float(np.nextafter(finite[0], -np.inf))}
    for value in finite:
        candidates.add(value)
        candidates.add(float(np.nextafter(value, np.inf)))
    return tuple(sorted(candidates))


def single_accept(trace: PredictionTrace, model_name: str, gate: SingleModelGate) -> bool:
    return trace.model_rankings[model_name][0].score >= gate.threshold


def fusion_accept(trace: PredictionTrace, gate: FusionGate) -> bool:
    if len(trace.fusion_ranking) < 2:
        raise ArtifactError("fusion rejection requires at least two ranked monuments")
    winner = trace.fusion_ranking[0].monument_id
    supporters = 0
    for name, threshold in gate.model_thresholds.items():
        ranking = trace.model_rankings[name]
        if ranking[0].monument_id == winner and ranking[0].score >= threshold:
            supporters += 1
    margin = trace.fusion_ranking[0].score - trace.fusion_ranking[1].score
    return supporters >= gate.minimum_winner_models and margin >= gate.margin_threshold


def _known_metrics(
    known: Sequence[LabeledTrace],
    strategy: str,
    accepts: Sequence[bool],
) -> GateMetrics:
    accepted = sum(accepts)
    correct = sum(
        accept and sample.trace.ranking(strategy)[0].monument_id == sample.monument_id
        for sample, accept in zip(known, accepts, strict=True)
    )
    return GateMetrics(accepted=accepted, correctly_accepted=correct, total=len(known))


def calibrate_single_model(
    model_name: str,
    known: Sequence[LabeledTrace],
    negatives: Sequence[PredictionTrace],
    *,
    maximum_false_acceptance: float,
    allow_empty: bool = False,
) -> tuple[SingleModelGate, GateMetrics, int]:
    allowed = math.floor(maximum_false_acceptance * len(negatives))
    values = [sample.trace.model_rankings[model_name][0].score for sample in known]
    values.extend(trace.model_rankings[model_name][0].score for trace in negatives)
    choices: list[tuple[int, int, float, SingleModelGate, GateMetrics, int]] = []
    for threshold in _candidate_thresholds(values):
        gate = SingleModelGate(threshold=threshold)
        negative_accepts = sum(single_accept(trace, model_name, gate) for trace in negatives)
        if negative_accepts > allowed:
            continue
        known_accepts = [single_accept(sample.trace, model_name, gate) for sample in known]
        metrics = _known_metrics(known, model_name, known_accepts)
        if metrics.correctly_accepted == 0:
            continue
        choices.append(
            (
                metrics.correctly_accepted,
                metrics.accepted,
                -threshold,
                gate,
                metrics,
                negative_accepts,
            )
        )
    if not choices:
        if allow_empty:
            reject_all = float(np.nextafter(max(values), np.inf))
            return (
                SingleModelGate(threshold=reject_all),
                GateMetrics(accepted=0, correctly_accepted=0, total=len(known)),
                0,
            )
        raise ArtifactError(f"no nontrivial {model_name} gate meets the OOD target")
    _, _, _, gate, metrics, negative_accepts = max(choices, key=lambda item: item[:3])
    return gate, metrics, negative_accepts


def calibrate_fusion_gate(
    known: Sequence[LabeledTrace],
    negatives: Sequence[PredictionTrace],
    *,
    minimum_winner_models: int,
    maximum_false_acceptance: float,
) -> tuple[FusionGate, GateMetrics, int]:
    if minimum_winner_models != 2 or len(MODEL_NAMES) != 3:
        raise ArtifactError("joint fusion calibration requires two-of-three model support")
    allowed = math.floor(maximum_false_acceptance * len(negatives))
    traces = [sample.trace for sample in known] + list(negatives)
    known_count = len(known)
    margins = np.asarray(
        [trace.fusion_ranking[0].score - trace.fusion_ranking[1].score for trace in traces],
        dtype=np.float64,
    )
    correct_known = np.asarray(
        [
            sample.trace.fusion_ranking[0].monument_id == sample.monument_id
            for sample in known
        ],
        dtype=bool,
    )

    threshold_masks: dict[str, list[tuple[float, np.ndarray]]] = {}
    for name in MODEL_NAMES:
        scores = [trace.model_rankings[name][0].score for trace in traces]
        winner_matches = np.asarray(
            [
                trace.model_rankings[name][0].monument_id
                == trace.fusion_ranking[0].monument_id
                for trace in traces
            ],
            dtype=bool,
        )
        unique_masks: dict[bytes, tuple[float, np.ndarray]] = {}
        for threshold in _candidate_thresholds(scores):
            mask = winner_matches & (np.asarray(scores) >= threshold)
            unique_masks.setdefault(mask.tobytes(), (threshold, mask))
        threshold_masks[name] = list(unique_masks.values())

    choice: tuple[tuple[float, ...], FusionGate, GateMetrics, int] | None = None
    support_cache: dict[bytes, tuple[float, GateMetrics, int] | None] = {}
    all_margin_floor = float(np.nextafter(float(np.min(margins)), -np.inf))
    for first, second, third in product(*(threshold_masks[name] for name in MODEL_NAMES)):
        support = (first[1] & second[1]) | (first[1] & third[1]) | (second[1] & third[1])
        support_key = support.tobytes()
        cached = support_cache.get(support_key)
        if support_key not in support_cache:
            eligible_negative_margins = margins[known_count:][support[known_count:]]
            if len(eligible_negative_margins) > allowed:
                descending = np.sort(eligible_negative_margins)[::-1]
                margin_threshold = float(np.nextafter(descending[allowed], np.inf))
            else:
                margin_threshold = all_margin_floor
            accepted = support & (margins >= margin_threshold)
            negative_accepts = int(np.count_nonzero(accepted[known_count:]))
            known_accepts = accepted[:known_count]
            metrics = GateMetrics(
                accepted=int(np.count_nonzero(known_accepts)),
                correctly_accepted=int(np.count_nonzero(known_accepts & correct_known)),
                total=known_count,
            )
            cached = (
                (margin_threshold, metrics, negative_accepts)
                if negative_accepts <= allowed and metrics.correctly_accepted > 0
                else None
            )
            support_cache[support_key] = cached
        if cached is None:
            continue
        margin_threshold, metrics, negative_accepts = cached
        thresholds = (first[0], second[0], third[0])
        gate = FusionGate(
            model_thresholds=dict(zip(MODEL_NAMES, thresholds, strict=True)),
            margin_threshold=margin_threshold,
            minimum_winner_models=minimum_winner_models,
        )
        objective = (
            float(metrics.correctly_accepted),
            float(metrics.accepted),
            float(negative_accepts),
            -margin_threshold,
            *(-threshold for threshold in thresholds),
        )
        if choice is None or objective > choice[0]:
            choice = (objective, gate, metrics, negative_accepts)
    if choice is None:
        reject_thresholds = {
            name: float(
                np.nextafter(
                    max(trace.model_rankings[name][0].score for trace in traces),
                    np.inf,
                )
            )
            for name in MODEL_NAMES
        }
        reject_margin = float(np.nextafter(float(np.max(margins)), np.inf))
        return (
            FusionGate(
                model_thresholds=reject_thresholds,
                margin_threshold=reject_margin,
                minimum_winner_models=minimum_winner_models,
            ),
            GateMetrics(accepted=0, correctly_accepted=0, total=len(known)),
            0,
        )
    _, gate, metrics, negative_accepts = choice
    return gate, metrics, negative_accepts


def calibrate(
    known: Sequence[LabeledTrace],
    negatives: Sequence[PredictionTrace],
    *,
    maximum_false_acceptance: float = 0.05,
    minimum_winner_models: int = 2,
    expected_negative_count: int | None = None,
) -> CalibrationResult:
    if not known:
        raise ArtifactError("known calibration set must not be empty")
    if not negatives:
        raise ArtifactError("OOD calibration set must not be empty")
    if expected_negative_count is not None and len(negatives) != expected_negative_count:
        raise ArtifactError(
            f"calibration requires exactly {expected_negative_count} OOD negatives"
        )
    if any(sample.monument_id is None for sample in known):
        raise ArtifactError("known calibration samples require labels")

    single_gates: dict[str, SingleModelGate] = {}
    metrics: dict[str, GateMetrics] = {}
    negative_accepts: dict[str, int] = {}
    for name in MODEL_NAMES:
        gate, model_metrics, model_negative_accepts = calibrate_single_model(
            name,
            known,
            negatives,
            maximum_false_acceptance=maximum_false_acceptance,
            allow_empty=True,
        )
        single_gates[name] = gate
        metrics[name] = model_metrics
        negative_accepts[name] = model_negative_accepts

    fusion_gate, fusion_metrics, fusion_negative_accepts = calibrate_fusion_gate(
        known,
        negatives,
        minimum_winner_models=minimum_winner_models,
        maximum_false_acceptance=maximum_false_acceptance,
    )
    metrics["fusion"] = fusion_metrics
    negative_accepts["fusion"] = fusion_negative_accepts

    if all(model_metrics.correctly_accepted == 0 for model_metrics in metrics.values()):
        raise ArtifactError("no nontrivial operational gate meets the OOD target")

    model_order = {name: -index for index, name in enumerate(MODEL_NAMES)}
    best_single = max(
        MODEL_NAMES,
        key=lambda name: (
            metrics[name].correctly_accepted,
            metrics[name].selective_accuracy,
            metrics[name].coverage,
            model_order[name],
        ),
    )
    active_strategy = best_single
    if (
        fusion_metrics.correctly_accepted > metrics[best_single].correctly_accepted
        and fusion_metrics.selective_accuracy >= metrics[best_single].selective_accuracy
    ):
        active_strategy = "fusion"
    return CalibrationResult(
        single_gates=single_gates,
        fusion_gate=fusion_gate,
        active_strategy=active_strategy,
        known_metrics=metrics,
        negative_accepts=negative_accepts,
    )


def gates_from_metadata(
    value: Mapping[str, object],
) -> tuple[dict[str, SingleModelGate], FusionGate]:
    try:
        single_raw = value["single"]
        fusion_raw = value["fusion"]
        if not isinstance(single_raw, dict) or not isinstance(fusion_raw, dict):
            raise TypeError
        single = {
            name: SingleModelGate(threshold=float(single_raw[name]["threshold"]))
            for name in MODEL_NAMES
        }
        thresholds = fusion_raw["model_thresholds"]
        if not isinstance(thresholds, dict):
            raise TypeError
        fusion = FusionGate(
            model_thresholds={name: float(thresholds[name]) for name in MODEL_NAMES},
            margin_threshold=float(fusion_raw["margin_threshold"]),
            minimum_winner_models=int(fusion_raw["minimum_winner_models"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ArtifactError("artifact rejection gates are invalid") from exc
    return single, fusion
