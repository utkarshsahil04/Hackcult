"""Frozen-artifact evaluation and auditable report generation."""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import statistics
import tempfile
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path, PurePosixPath
from typing import Any

from PIL import Image

from raahein_ml.config import (
    MODEL_NAMES,
    MLConfig,
    load_config,
    semantic_csv_hash,
    sha256_file,
)
from raahein_ml.dedupe import phash_hamming_distance
from raahein_ml.manifest import (
    ALLOWED_LICENSES,
    NEGATIVE_FIELDS,
    ManifestError,
    ManifestRow,
    analyze_image,
    read_manifest,
    validate_manifests,
    validate_provenance_url,
)
from raahein_ml.schemas import ArtifactError, PredictionTrace, RecognitionError
from raahein_ml.service import RecognitionService, resolve_artifact_path

STRATEGIES = (*MODEL_NAMES, "fusion")
OOD_CATEGORIES = ("non_target_monument", "everyday_scene")
REPORT_SCHEMA_VERSION = 1
TABLE_START = "<!-- ML_EVALUATION_RESULTS_START -->"
TABLE_END = "<!-- ML_EVALUATION_RESULTS_END -->"


@dataclass(frozen=True, slots=True)
class PositivePrediction:
    monument_id: str
    ranking: tuple[str, ...]
    accepted: bool


@dataclass(frozen=True, slots=True)
class OODPrediction:
    category: str
    accepted: bool


@dataclass(frozen=True, slots=True)
class OODRow:
    image_id: str
    category: str
    local_path: str
    source_id: str = ""
    source_page_url: str = ""
    download_url: str = ""
    author: str = ""
    license_id: str = ""
    license_url: str = ""
    attribution: str = ""
    sha256: str = ""
    phash: str = ""


def positive_metrics(predictions: Sequence[PositivePrediction]) -> dict[str, object]:
    if not predictions:
        raise ValueError("positive evaluation set must not be empty")
    if any(not prediction.ranking for prediction in predictions):
        raise ValueError("positive predictions require a ranking")
    total = len(predictions)
    top_1 = sum(prediction.monument_id in prediction.ranking[:1] for prediction in predictions)
    top_3 = sum(prediction.monument_id in prediction.ranking[:3] for prediction in predictions)
    recall_5 = sum(prediction.monument_id in prediction.ranking[:5] for prediction in predictions)
    accepted = sum(prediction.accepted for prediction in predictions)
    correctly_accepted = sum(
        prediction.accepted and prediction.ranking[0] == prediction.monument_id
        for prediction in predictions
    )
    return {
        "sample_count": total,
        "top_1": top_1 / total,
        "top_3": top_3 / total,
        "recall_at_5": recall_5 / total,
        "accepted_coverage": accepted / total,
        "correct_acceptance": correctly_accepted / total,
        "selective_accuracy": correctly_accepted / accepted if accepted else None,
        "known_false_rejection_rate": (total - accepted) / total,
    }


def _ood_metrics_subset(predictions: Sequence[OODPrediction]) -> dict[str, object]:
    if not predictions:
        raise ValueError("OOD evaluation subset must not be empty")
    total = len(predictions)
    accepted = sum(prediction.accepted for prediction in predictions)
    return {
        "sample_count": total,
        "rejection_rate": (total - accepted) / total,
        "false_acceptance_rate": accepted / total,
        "false_acceptance_count": accepted,
    }


def ood_metrics(predictions: Sequence[OODPrediction]) -> dict[str, object]:
    if not predictions:
        raise ValueError("OOD evaluation set must not be empty")
    categories = {prediction.category for prediction in predictions}
    unknown = categories - set(OOD_CATEGORIES)
    if unknown:
        raise ValueError(f"unknown OOD categories: {sorted(unknown)}")
    result = _ood_metrics_subset(predictions)
    result["by_category"] = {
        category: _ood_metrics_subset(
            [prediction for prediction in predictions if prediction.category == category]
        )
        for category in OOD_CATEGORIES
    }
    return result


def validate_evaluation_counts(
    internal_rows: Sequence[ManifestRow],
    independent_rows: Sequence[ManifestRow],
    ood_rows: Sequence[OODRow],
    config: MLConfig,
) -> None:
    internal = [row for row in internal_rows if row.status == "accepted" and row.split == "test"]
    counts = Counter(row.monument_id for row in internal)
    if set(counts) != set(config.canonical_monument_ids):
        raise ArtifactError("internal final test must cover all canonical monuments")
    if min(counts.values()) < config.split.test_per_class:
        raise ArtifactError("internal final test has too few images per monument")
    independent = [
        row
        for row in independent_rows
        if row.status == "accepted" and row.split == "independent_test"
    ]
    if len(independent) != config.evaluation.independent_positive_count:
        raise ArtifactError(
            f"independent final test requires {config.evaluation.independent_positive_count} images"
        )
    if {row.monument_id for row in independent} != set(config.canonical_monument_ids):
        raise ArtifactError("independent final test must cover all canonical monuments")
    if len(ood_rows) != config.calibration.test_negative_count:
        raise ArtifactError(
            f"OOD final test requires {config.calibration.test_negative_count} images"
        )
    category_counts = Counter(row.category for row in ood_rows)
    if set(category_counts) != set(OOD_CATEGORIES):
        raise ArtifactError("OOD final test has invalid categories")
    expected_per_category = config.calibration.test_negative_count // len(OOD_CATEGORIES)
    if any(category_counts[category] != expected_per_category for category in OOD_CATEGORIES):
        raise ArtifactError("OOD final test must be category-balanced")


def _read_ood_rows(path: Path) -> tuple[OODRow, ...]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != NEGATIVE_FIELDS:
                raise ArtifactError(f"{path} has an unexpected OOD header")
            rows = tuple(
                OODRow(
                    image_id=(row["image_id"] or "").strip(),
                    category=(row["category"] or "").strip(),
                    local_path=(row["local_path"] or "").strip(),
                    source_id=(row["source_id"] or "").strip(),
                    source_page_url=(row["source_page_url"] or "").strip(),
                    download_url=(row["download_url"] or "").strip(),
                    author=(row["author"] or "").strip(),
                    license_id=(row["license_id"] or "").strip(),
                    license_url=(row["license_url"] or "").strip(),
                    attribution=(row["attribution"] or "").strip(),
                    sha256=(row["sha256"] or "").strip(),
                    phash=(row["phash"] or "").strip(),
                )
                for row in reader
            )
    except OSError as exc:
        raise ArtifactError(f"cannot read OOD manifest: {path}") from exc
    if len({row.image_id for row in rows}) != len(rows):
        raise ArtifactError("OOD image IDs must be unique")
    if len({row.source_id for row in rows}) != len(rows):
        raise ArtifactError("OOD source IDs must be unique")
    for row in rows:
        required = (
            row.image_id,
            row.category,
            row.local_path,
            row.source_id,
            row.source_page_url,
            row.download_url,
            row.author,
            row.license_id,
            row.license_url,
            row.attribution,
            row.sha256,
            row.phash,
        )
        if any(not value for value in required):
            raise ArtifactError(f"OOD row has incomplete provenance: {row.image_id}")
        if row.license_id not in ALLOWED_LICENSES:
            raise ArtifactError(f"OOD row has a disallowed licence: {row.image_id}")
        for value in (row.source_page_url, row.download_url, row.license_url):
            try:
                validate_provenance_url(value, "OOD provenance URL")
            except ManifestError as exc:
                raise ArtifactError(f"OOD row has an invalid URL: {row.image_id}") from exc
        if len(row.sha256) != 64 or len(row.phash) != 16:
            raise ArtifactError(f"OOD row has invalid fingerprints: {row.image_id}")
    return tuple(sorted(rows, key=lambda row: row.image_id))


def _validate_negative_fingerprints(rows: Sequence[OODRow], config: MLConfig) -> None:
    for row in rows:
        analysis = analyze_image(_local_image_path(config.repository_root, row.local_path))
        if (analysis.sha256, analysis.phash) != (row.sha256, row.phash):
            raise ArtifactError(f"OOD fingerprint differs for {row.image_id}")


def _validate_final_set_disjointness(
    final_ood: Sequence[OODRow],
    calibration_ood: Sequence[OODRow],
    positive_rows: Sequence[ManifestRow],
) -> None:
    def overlaps(
        left_sha: str,
        left_phash: str,
        right_sha: str,
        right_phash: str,
    ) -> bool:
        return left_sha == right_sha or phash_hamming_distance(left_phash, right_phash) <= 4

    def overlaps_positive(negative: OODRow, positive: ManifestRow) -> bool:
        return (
            overlaps(negative.sha256, negative.phash, positive.sha256, positive.phash)
            or negative.source_id == positive.source_id
            or negative.source_page_url == positive.source_page_url
            or negative.download_url == positive.download_url
            or negative.local_path == positive.local_path
        )

    for group_name, rows in (("final OOD", final_ood), ("calibration OOD", calibration_ood)):
        for left, right in combinations(rows, 2):
            if (
                overlaps(left.sha256, left.phash, right.sha256, right.phash)
                or left.source_id == right.source_id
                or left.source_page_url == right.source_page_url
                or left.download_url == right.download_url
                or left.local_path == right.local_path
            ):
                raise ArtifactError(
                    f"{group_name} rows overlap: {left.image_id}/{right.image_id}"
                )

    for final in final_ood:
        for calibration in calibration_ood:
            if (
                overlaps(final.sha256, final.phash, calibration.sha256, calibration.phash)
                or final.source_id == calibration.source_id
                or final.source_page_url == calibration.source_page_url
                or final.download_url == calibration.download_url
            ):
                raise ArtifactError(
                    f"final OOD {final.image_id} overlaps calibration OOD {calibration.image_id}"
                )
        for positive in positive_rows:
            if positive.status == "accepted" and overlaps_positive(final, positive):
                raise ArtifactError(
                    f"final OOD {final.image_id} overlaps positive {positive.image_id}"
                )
    for calibration in calibration_ood:
        for positive in positive_rows:
            if positive.status == "accepted" and overlaps_positive(calibration, positive):
                raise ArtifactError(
                    f"calibration OOD {calibration.image_id} overlaps positive "
                    f"{positive.image_id}"
                )


def _local_image_path(repository_root: Path, local_path: str) -> Path:
    pure = PurePosixPath(local_path)
    if pure.is_absolute() or ".." in pure.parts:
        raise ArtifactError(f"unsafe evaluation path: {local_path}")
    resolved = (repository_root / Path(*pure.parts)).resolve()
    try:
        resolved.relative_to(repository_root)
    except ValueError as exc:
        raise ArtifactError(f"evaluation path escapes repository: {local_path}") from exc
    return resolved


def _artifact_snapshot(path: Path) -> dict[str, str]:
    return {
        file.relative_to(path).as_posix(): sha256_file(file)
        for file in sorted(path.rglob("*"))
        if file.is_file()
    }


def _cuda_synchronize(device: str) -> None:
    if not device.startswith("cuda"):
        return
    try:
        import torch

        torch.cuda.synchronize(device)
    except ImportError:
        return


def _trace_image(
    service: RecognitionService,
    path: Path,
) -> tuple[PredictionTrace, float]:
    try:
        with Image.open(path) as image:
            image.load()
            _cuda_synchronize(service.config.device)
            started = time.perf_counter()
            trace = service.predict_trace(image)
            _cuda_synchronize(service.config.device)
            latency_ms = (time.perf_counter() - started) * 1000
    except (OSError, ValueError) as exc:
        raise ArtifactError(f"cannot decode evaluation image: {path}") from exc
    return trace, latency_ms


def _ranking_ids(trace: PredictionTrace, strategy: str) -> tuple[str, ...]:
    return tuple(item.monument_id for item in trace.ranking(strategy))


def _device_details(config: MLConfig) -> dict[str, object]:
    details: dict[str, object] = {
        "configured_device": config.device,
        "platform": platform.platform(),
        "python": platform.python_version(),
    }
    try:
        import torch

        details["torch_version"] = torch.__version__
        details["cuda_runtime"] = torch.version.cuda
        if config.device.startswith("cuda") and torch.cuda.is_available():
            details["gpu_name"] = torch.cuda.get_device_name(config.device)
    except ImportError:
        details["torch_version"] = None
    return details


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        raise ValueError("latency samples must not be empty")
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def evaluate_frozen_artifact(
    config: MLConfig,
    artifact_path: Path,
) -> dict[str, object]:
    artifact_path = resolve_artifact_path(artifact_path)
    before = _artifact_snapshot(artifact_path)
    internal_rows = list(read_manifest(config.paths.manifest))
    independent_rows = list(
        read_manifest(config.paths.manifest.parent / "independent_test.csv")
    )
    validate_manifests(
        internal_rows,
        independent_rows,
        config,
        rehash=True,
        require_independent_count=True,
    )
    ood_rows = list(_read_ood_rows(config.paths.manifest.parent / "test_negatives.csv"))
    calibration_ood = list(
        _read_ood_rows(config.paths.manifest.parent / "calibration_negatives.csv")
    )
    validate_evaluation_counts(internal_rows, independent_rows, ood_rows, config)
    if len(calibration_ood) != config.calibration.calibration_negative_count:
        raise ArtifactError(
            "calibration OOD set changed after artifact finalization or has the wrong count"
        )
    calibration_counts = Counter(row.category for row in calibration_ood)
    if set(calibration_counts) != set(OOD_CATEGORIES) or len(
        set(calibration_counts.values())
    ) != 1:
        raise ArtifactError("calibration OOD set must remain category-balanced")
    _validate_negative_fingerprints(ood_rows, config)
    _validate_negative_fingerprints(calibration_ood, config)
    _validate_final_set_disjointness(
        ood_rows,
        calibration_ood,
        [*internal_rows, *independent_rows],
    )

    service = RecognitionService(config, artifact_path=artifact_path)
    startup_started = time.perf_counter()
    service.start()
    startup_ms = (time.perf_counter() - startup_started) * 1000
    readiness = service.readiness
    if not readiness.ready:
        raise ArtifactError("recognition service did not become ready")
    bundle = service._bundle  # Evaluation reads immutable metadata; it never writes artifacts.
    if bundle is None:
        raise ArtifactError("recognition artifact was not retained after startup")
    if bundle.metadata["manifest_hash"] != semantic_csv_hash(config.paths.manifest):
        raise ArtifactError("finalized artifact does not match the current manifest")
    calibration_metadata = bundle.metadata.get("calibration")
    if not isinstance(calibration_metadata, dict):
        raise ArtifactError("finalized artifact lacks calibration provenance")
    frozen_final_inputs = {
        "independent_manifest_hash": semantic_csv_hash(
            config.paths.manifest.parent / "independent_test.csv"
        ),
        "test_negative_manifest_hash": semantic_csv_hash(
            config.paths.manifest.parent / "test_negatives.csv"
        ),
        "negative_manifest_hash": semantic_csv_hash(
            config.paths.manifest.parent / "calibration_negatives.csv"
        ),
    }
    if any(
        calibration_metadata.get(name) != value
        for name, value in frozen_final_inputs.items()
    ):
        raise ArtifactError("evaluation inputs differ from the hashes frozen at calibration")

    positive_by_strategy: dict[str, dict[str, list[PositivePrediction]]] = {
        strategy: {"internal_clean": [], "independent_positive": []}
        for strategy in STRATEGIES
    }
    ood_by_strategy: dict[str, list[OODPrediction]] = {
        strategy: [] for strategy in STRATEGIES
    }
    latencies: list[float] = []

    positive_sets = {
        "internal_clean": sorted(
            [row for row in internal_rows if row.status == "accepted" and row.split == "test"],
            key=lambda row: row.image_id,
        ),
        "independent_positive": sorted(
            [
                row
                for row in independent_rows
                if row.status == "accepted" and row.split == "independent_test"
            ],
            key=lambda row: row.image_id,
        ),
    }
    for dataset, rows in positive_sets.items():
        for row in rows:
            trace, latency = _trace_image(
                service, _local_image_path(config.repository_root, row.local_path)
            )
            latencies.append(latency)
            for strategy in STRATEGIES:
                positive_by_strategy[strategy][dataset].append(
                    PositivePrediction(
                        monument_id=row.monument_id,
                        ranking=_ranking_ids(trace, strategy),
                        accepted=service.accepts(trace, strategy),
                    )
                )
    for row in ood_rows:
        trace, latency = _trace_image(
            service, _local_image_path(config.repository_root, row.local_path)
        )
        latencies.append(latency)
        for strategy in STRATEGIES:
            ood_by_strategy[strategy].append(
                OODPrediction(category=row.category, accepted=service.accepts(trace, strategy))
            )

    report: dict[str, object] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "artifact_id": bundle.artifact_id,
        "manifest_hash": bundle.metadata["manifest_hash"],
        "catalog_hash": bundle.metadata["catalog_hash"],
        "config_hash": bundle.metadata["config_hash"],
        "model_revisions": {
            name: bundle.metadata["models"][name]["revision"] for name in MODEL_NAMES
        },
        "thresholds": bundle.metadata["gates"],
        "active_strategy": bundle.active_strategy,
        "sample_counts": {
            "internal_clean": len(positive_sets["internal_clean"]),
            "independent_positive": len(positive_sets["independent_positive"]),
            "ood": len(ood_rows),
            "ood_by_category": dict(sorted(Counter(row.category for row in ood_rows).items())),
        },
        "startup_warmup_ms": startup_ms,
        "warm_latency_ms": {
            "scope": "all_three_encoders_plus_indexes",
            "sample_count": len(latencies),
            "p50": statistics.median(latencies),
            "p95": _percentile(latencies, 0.95),
        },
        "device": _device_details(config),
        "strategies": {
            strategy: {
                "internal_clean": positive_metrics(
                    positive_by_strategy[strategy]["internal_clean"]
                ),
                "independent_positive": positive_metrics(
                    positive_by_strategy[strategy]["independent_positive"]
                ),
                "ood": ood_metrics(ood_by_strategy[strategy]),
            }
            for strategy in STRATEGIES
        },
    }
    after = _artifact_snapshot(artifact_path)
    if before != after:
        raise ArtifactError("evaluation mutated the finalized artifact")
    return report


def _format_rate(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.1f}%"


def render_readme_table(report: Mapping[str, Any]) -> str:
    strategies = report.get("strategies")
    if not isinstance(strategies, dict) or set(strategies) != set(STRATEGIES):
        raise ValueError("evaluation report must contain all four strategies")
    lines = [
        "| Strategy | Dataset | N | Top-1 | Top-3 | Recall@5 | Coverage | "
        "Selective accuracy | OOD rejection | OOD false acceptance |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for strategy in STRATEGIES:
        result = strategies[strategy]
        for dataset in ("internal_clean", "independent_positive"):
            metrics = result[dataset]
            lines.append(
                "| "
                + " | ".join(
                    (
                        strategy,
                        dataset,
                        str(metrics["sample_count"]),
                        _format_rate(metrics["top_1"]),
                        _format_rate(metrics["top_3"]),
                        _format_rate(metrics["recall_at_5"]),
                        _format_rate(metrics["accepted_coverage"]),
                        _format_rate(metrics["selective_accuracy"]),
                        "n/a",
                        "n/a",
                    )
                )
                + " |"
            )
        metrics = result["ood"]
        lines.append(
            "| "
            + " | ".join(
                (
                    strategy,
                    "ood",
                    str(metrics["sample_count"]),
                    "n/a",
                    "n/a",
                    "n/a",
                    "n/a",
                    "n/a",
                    _format_rate(metrics["rejection_rate"]),
                    _format_rate(metrics["false_acceptance_rate"]),
                )
            )
            + " |"
        )
    return "\n".join(lines)


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        with suppress(FileNotFoundError):
            os.unlink(temporary_name)
        raise


def write_report(path: Path, report: Mapping[str, object]) -> None:
    payload = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    _atomic_write(path, payload.encode("utf-8"))


def validate_report_path(path: Path, config: MLConfig, artifact_path: Path) -> Path:
    resolved = path.expanduser()
    if not resolved.is_absolute():
        resolved = config.repository_root / resolved
    resolved = resolved.resolve()
    protected_directories = (
        artifact_path.resolve(),
        config.paths.manifest.parent.resolve(),
        config.paths.source_catalog.parent.resolve(),
        config.config_path.parent.resolve(),
    )
    protected_files = {
        config.paths.canonical_monuments.resolve(),
        (config.repository_root / "README.md").resolve(),
    }
    if resolved in protected_files or any(
        resolved == directory or directory in resolved.parents
        for directory in protected_directories
    ):
        raise ValueError("evaluation report path targets a frozen input or artifact")
    if resolved.suffix.lower() != ".json":
        raise ValueError("evaluation report output must be a JSON file")
    return resolved


def update_readme(readme_path: Path, report: Mapping[str, Any]) -> None:
    table = render_readme_table(report)
    block = f"{TABLE_START}\n{table}\n{TABLE_END}"
    try:
        current = readme_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read README: {readme_path}") from exc
    if TABLE_START in current or TABLE_END in current:
        if current.count(TABLE_START) != 1 or current.count(TABLE_END) != 1:
            raise ValueError("README evaluation markers are malformed")
        start = current.index(TABLE_START)
        end = current.index(TABLE_END) + len(TABLE_END)
        updated = current[:start] + block + current[end:]
    else:
        separator = "" if current.endswith("\n") else "\n"
        updated = f"{current}{separator}\n## Recognition evaluation\n\n{block}\n"
    _atomic_write(readme_path, updated.encode("utf-8"))


def verify_readme_report(readme_path: Path, report: Mapping[str, Any]) -> None:
    expected = f"{TABLE_START}\n{render_readme_table(report)}\n{TABLE_END}"
    if expected not in readme_path.read_text(encoding="utf-8"):
        raise ValueError("README evaluation table does not match evaluation.json")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="path to models.yaml")
    parser.add_argument("--artifact", type=Path, help="finalized artifact directory")
    parser.add_argument("--report", type=Path, help="evaluation JSON output")
    parser.add_argument("--update-readme", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        artifact = resolve_artifact_path(args.artifact or config.paths.artifacts)
        report_path = validate_report_path(
            args.report
            or config.repository_root / "ml" / "reports" / "evaluation.json",
            config,
            artifact,
        )
        report = evaluate_frozen_artifact(config, artifact)
        write_report(report_path, report)
        if args.update_readme:
            readme = config.repository_root / "README.md"
            update_readme(readme, report)
            verify_readme_report(readme, report)
    except (ManifestError, OSError, RecognitionError, ValueError) as exc:
        print(f"evaluation error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
