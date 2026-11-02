from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from raahein_ml.config import MLConfig
from raahein_ml.evaluate import (
    OOD_CATEGORIES,
    STRATEGIES,
    OODPrediction,
    OODRow,
    PositivePrediction,
    _validate_final_set_disjointness,
    ood_metrics,
    positive_metrics,
    render_readme_table,
    update_readme,
    validate_evaluation_counts,
    validate_report_path,
    verify_readme_report,
)
from raahein_ml.manifest import ManifestRow
from raahein_ml.schemas import ArtifactError


def _row(
    image_id: str,
    monument_id: str,
    *,
    collection: str,
    split: str,
) -> ManifestRow:
    return ManifestRow(
        image_id=image_id,
        source_id=image_id,
        collection=collection,
        monument_id=monument_id,
        component="",
        local_path=f"data/raw/{image_id}",
        source_group=image_id,
        source_page_url=f"https://example.org/source/{image_id}",
        download_url=f"https://example.org/download/{image_id}",
        author="Author",
        license_id="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        attribution="Author, CC BY 4.0",
        image_format="jpeg",
        width=300,
        height=300,
        file_size_bytes=100,
        sha256=f"{len(image_id):064x}",
        phash=f"{len(image_id):016x}",
        duplicate_group=f"dup-{image_id}",
        split_group=f"split-{image_id}",
        status="accepted",
        split=split,
    )


def test_positive_metrics_keep_rankings_for_uncertain_results() -> None:
    metrics = positive_metrics(
        [
            PositivePrediction("a", ("a", "b", "c", "d", "e"), False),
            PositivePrediction("b", ("a", "c", "b", "d", "e"), True),
            PositivePrediction("e", ("a", "b", "c", "d", "e"), True),
        ]
    )
    assert metrics["top_1"] == pytest.approx(1 / 3)
    assert metrics["top_3"] == pytest.approx(2 / 3)
    assert metrics["recall_at_5"] == 1.0
    assert metrics["accepted_coverage"] == pytest.approx(2 / 3)
    assert metrics["correct_acceptance"] == 0.0
    assert metrics["selective_accuracy"] == 0.0
    assert metrics["known_false_rejection_rate"] == pytest.approx(1 / 3)
    with pytest.raises(ValueError, match="must not be empty"):
        positive_metrics([])


def test_ood_metrics_report_categories_and_false_acceptance() -> None:
    predictions = [
        OODPrediction("non_target_monument", index == 0) for index in range(25)
    ] + [OODPrediction("everyday_scene", False) for _ in range(25)]
    metrics = ood_metrics(predictions)
    assert metrics["sample_count"] == 50
    assert metrics["false_acceptance_rate"] == 0.02
    assert metrics["rejection_rate"] == 0.98
    assert metrics["by_category"]["non_target_monument"]["false_acceptance_count"] == 1


def test_exact_final_dataset_counts_are_enforced(cpu_config: MLConfig) -> None:
    internal = [
        _row(f"internal-{slug}-{index}", slug, collection="curated", split="test")
        for slug in cpu_config.canonical_monument_ids
        for index in range(2)
    ]
    independent = [
        _row(
            f"independent-{index}",
            cpu_config.canonical_monument_ids[index % 15],
            collection="independent",
            split="independent_test",
        )
        for index in range(20)
    ]
    ood = [
        OODRow(f"ood-{index}", OOD_CATEGORIES[index // 25], f"data/raw/ood-{index}")
        for index in range(50)
    ]
    validate_evaluation_counts(internal, independent, ood, cpu_config)
    with pytest.raises(ArtifactError, match="requires 20"):
        validate_evaluation_counts(internal, independent[:-1], ood, cpu_config)
    unbalanced = [replace(row, category="everyday_scene") for row in ood]
    with pytest.raises(ArtifactError, match="invalid categories"):
        validate_evaluation_counts(internal, independent, unbalanced, cpu_config)


def _report() -> dict[str, object]:
    positive = {
        "sample_count": 30,
        "top_1": 0.8,
        "top_3": 0.9,
        "recall_at_5": 0.95,
        "accepted_coverage": 0.75,
        "correct_acceptance": 0.7,
        "selective_accuracy": 0.9333333333,
        "known_false_rejection_rate": 0.25,
    }
    ood = {
        "sample_count": 50,
        "rejection_rate": 0.96,
        "false_acceptance_rate": 0.04,
        "false_acceptance_count": 2,
        "by_category": {},
    }
    return {
        "strategies": {
            strategy: {
                "internal_clean": dict(positive),
                "independent_positive": {**positive, "sample_count": 20},
                "ood": dict(ood),
            }
            for strategy in STRATEGIES
        }
    }


def test_readme_table_is_generated_and_verified_from_report(tmp_path: Path) -> None:
    report = _report()
    readme = tmp_path / "README.md"
    readme.write_text("# Project\n", encoding="utf-8")
    update_readme(readme, report)
    verify_readme_report(readme, report)
    first = readme.read_text(encoding="utf-8")
    assert "80.0%" in first
    assert render_readme_table(report) in first
    update_readme(readme, report)
    assert readme.read_text(encoding="utf-8") == first

    changed = _report()
    changed["strategies"]["fusion"]["internal_clean"]["top_1"] = 0.1
    with pytest.raises(ValueError, match="does not match"):
        verify_readme_report(readme, changed)


def test_ood_rows_must_be_unique_within_each_set() -> None:
    first = OODRow(
        "one",
        "everyday_scene",
        "data/raw/one",
        source_id="one",
        source_page_url="https://example.org/one",
        download_url="https://example.org/download/one",
        sha256="1" * 64,
        phash="0" * 16,
    )
    duplicate = replace(
        first,
        image_id="two",
        source_id="two",
        source_page_url="https://example.org/two",
        download_url="https://example.org/download/two",
    )
    with pytest.raises(ArtifactError, match="final OOD rows overlap"):
        _validate_final_set_disjointness([first, duplicate], [], [])


def test_report_path_cannot_target_frozen_inputs(
    tmp_path: Path, cpu_config: MLConfig
) -> None:
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    with pytest.raises(ValueError, match="frozen input"):
        validate_report_path(artifact / "metadata.json", cpu_config, artifact)
    with pytest.raises(ValueError, match="frozen input"):
        validate_report_path(cpu_config.paths.manifest, cpu_config, artifact)
    output = validate_report_path(tmp_path / "evaluation.json", cpu_config, artifact)
    assert output == (tmp_path / "evaluation.json").resolve()
