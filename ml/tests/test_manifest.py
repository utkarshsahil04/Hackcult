from __future__ import annotations

import hashlib
import random
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image

from raahein_ml.config import MLConfig
from raahein_ml.dedupe import ImageFingerprint, ReviewPair, analyze_duplicates
from raahein_ml.manifest import (
    ALLOWED_LICENSES,
    ImageRejected,
    ManifestError,
    ManifestRow,
    SourceRecord,
    _check_leakage,
    analyze_image,
    assign_splits,
    read_manifest,
    validate_source,
    write_manifest,
)


def _source(**overrides: str) -> SourceRecord:
    values = {
        "source_id": "taj-001",
        "collection": "curated",
        "monument_id": "taj-mahal",
        "component": "",
        "source_page_url": "https://commons.wikimedia.org/wiki/File:Taj.jpg",
        "download_url": "https://upload.wikimedia.org/taj.jpg",
        "author": "Example Author",
        "license_id": "CC-BY-4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": "Example Author, CC BY 4.0",
        "source_group": "taj-001",
    }
    values.update(overrides)
    return SourceRecord(**values)


def _manifest_row(
    image_id: str,
    monument_id: str,
    split_group: str,
    *,
    split: str = "",
) -> ManifestRow:
    number = int(hashlib.sha256(image_id.encode()).hexdigest()[:16], 16)
    return ManifestRow(
        image_id=image_id,
        source_id=image_id,
        collection="curated",
        monument_id=monument_id,
        component="",
        local_path=f"data/raw/{image_id}",
        source_group=split_group,
        source_page_url=f"https://example.org/source/{image_id}",
        download_url=f"https://example.org/download/{image_id}",
        author="Author",
        license_id="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        attribution="Author, CC BY 4.0",
        image_format="png",
        width=300,
        height=300,
        file_size_bytes=1000,
        sha256=hashlib.sha256(image_id.encode()).hexdigest(),
        phash=f"{number:016x}",
        duplicate_group=f"dup-{image_id}",
        split_group=split_group,
        status="accepted",
        split=split,
    )


@pytest.mark.parametrize("license_id", sorted(ALLOWED_LICENSES))
def test_license_allowlist_accepts_only_supported_terms(
    cpu_config: MLConfig, license_id: str
) -> None:
    validate_source(
        _source(license_id=license_id),
        set(cpu_config.canonical_monument_ids),
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("license_id", "CC-BY-NC-4.0"),
        ("source_page_url", "http://example.org/image"),
        ("download_url", "https://gettyimages.com/stock.jpg"),
        ("author", ""),
        ("source_id", "../escape"),
        ("monument_id", "not-canonical"),
    ],
)
def test_source_validation_rejects_unusable_provenance(
    cpu_config: MLConfig, field: str, value: str
) -> None:
    with pytest.raises(ManifestError):
        validate_source(_source(**{field: value}), set(cpu_config.canonical_monument_ids))


def test_image_analysis_is_deterministic_and_exif_aware(tmp_path: Path) -> None:
    path = tmp_path / "oriented.jpg"
    image = Image.new("RGB", (240, 320), (20, 80, 140))
    exif = image.getexif()
    exif[274] = 6
    image.save(path, exif=exif)

    first = analyze_image(path)
    second = analyze_image(path)
    assert (first.width, first.height) == (320, 240)
    assert first.sha256 == second.sha256
    assert first.phash == second.phash
    assert len(first.phash) == 16


def test_transparency_is_composited_on_white(tmp_path: Path) -> None:
    transparent = tmp_path / "transparent.png"
    white = tmp_path / "white.png"
    Image.new("RGBA", (256, 256), (255, 0, 0, 0)).save(transparent)
    Image.new("RGB", (256, 256), "white").save(white)
    assert analyze_image(transparent).phash == analyze_image(white).phash


def test_corrupt_and_animated_images_are_quarantinable(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.jpg"
    corrupt.write_bytes(b"not an image")
    with pytest.raises(ImageRejected, match="corrupt_image"):
        analyze_image(corrupt)

    animated = tmp_path / "animated.gif"
    frames = [Image.new("RGB", (256, 256), color) for color in ("red", "blue")]
    frames[0].save(animated, save_all=True, append_images=frames[1:], duration=10, loop=0)
    with pytest.raises(ImageRejected, match="animated_image"):
        analyze_image(animated)


def _fingerprint(
    image_id: str,
    *,
    monument_id: str = "taj-mahal",
    collection: str = "curated",
    source_group: str | None = None,
    sha256: str | None = None,
    phash: str = "0000000000000000",
    width: int = 300,
    height: int = 300,
    eligible: bool = True,
) -> ImageFingerprint:
    return ImageFingerprint(
        image_id=image_id,
        monument_id=monument_id,
        collection=collection,
        source_group=source_group or image_id,
        sha256=sha256 or hashlib.sha256(image_id.encode()).hexdigest(),
        phash=phash,
        width=width,
        height=height,
        file_size_bytes=width * height,
        eligible=eligible,
    )


def test_duplicate_clusters_keep_best_and_quarantine_ambiguous_labels() -> None:
    records = [
        _fingerprint("a", sha256="1" * 64, width=300, height=300),
        _fingerprint("b", sha256="1" * 64, width=500, height=400),
        _fingerprint("c", phash="aaaaaaaaaaaaaaaa"),
        _fingerprint("d", phash="aaaaaaaaaaaaaab5"),
        _fingerprint("e", monument_id="taj-mahal", phash="ffffffffffffffff"),
        _fingerprint("f", monument_id="red-fort", phash="ffffffffffffffff"),
        _fingerprint("g", collection="curated", phash="0f0f0f0f0f0f0f0f"),
        _fingerprint("h", collection="independent", phash="0f0f0f0f0f0f0f0f"),
    ]
    result = analyze_duplicates(records)
    assert result.outcomes["b"].status == "accepted"
    assert result.outcomes["a"].exclusion_reason == "inferior_duplicate"
    assert result.outcomes["a"].duplicate_of_image_id == "b"
    assert result.outcomes["e"].exclusion_reason == "cross_label_duplicate"
    assert result.outcomes["f"].exclusion_reason == "cross_label_duplicate"
    assert result.outcomes["g"].exclusion_reason == "cross_collection_duplicate"
    assert result.outcomes["h"].exclusion_reason == "cross_collection_duplicate"
    assert any(not pair.decision for pair in result.review_pairs)


def test_manual_different_decision_prevents_distance_five_merge() -> None:
    left = _fingerprint("left", phash="0000000000000000")
    right = _fingerprint("right", phash="000000000000001f")
    review = ReviewPair(
        left_image_id="left",
        left_monument_id="taj-mahal",
        right_image_id="right",
        right_monument_id="taj-mahal",
        hamming_distance=5,
        decision="different",
        reviewer="reviewer",
    )
    result = analyze_duplicates([left, right], {review.key: review})
    assert result.outcomes["left"].duplicate_group != result.outcomes["right"].duplicate_group
    assert not result.has_pending_review


def test_changed_distance_invalidates_manual_review() -> None:
    left = _fingerprint("left", phash="0000000000000000")
    right = _fingerprint("right", phash="000000000000003f")
    stale = ReviewPair(
        left_image_id="left",
        left_monument_id="taj-mahal",
        right_image_id="right",
        right_monument_id="taj-mahal",
        hamming_distance=5,
        decision="different",
        reviewer="reviewer",
    )
    result = analyze_duplicates([left, right], {stale.key: stale})
    assert result.has_pending_review
    assert result.review_pairs[0].hamming_distance == 6
    assert result.review_pairs[0].decision == ""


def test_ineligible_panorama_cannot_replace_valid_duplicate() -> None:
    tiny_side = _fingerprint(
        "panorama",
        sha256="2" * 64,
        width=1000,
        height=100,
        eligible=False,
    )
    valid = _fingerprint(
        "valid",
        sha256="2" * 64,
        width=300,
        height=300,
        eligible=True,
    )
    result = analyze_duplicates([tiny_side, valid])
    assert result.outcomes["valid"].status == "accepted"
    assert result.outcomes["panorama"].duplicate_of_image_id == "valid"


def test_deterministic_balanced_split_is_input_order_independent(
    cpu_config: MLConfig,
) -> None:
    rows = [
        _manifest_row(f"{slug}-{index:02d}", slug, f"{slug}-{index:02d}")
        for slug in cpu_config.canonical_monument_ids
        for index in range(12)
    ]
    shuffled = list(rows)
    random.Random(99).shuffle(shuffled)
    first = assign_splits(rows, cpu_config)
    second = assign_splits(shuffled, cpu_config)
    assert {row.image_id: row.split for row in first} == {
        row.image_id: row.split for row in second
    }
    counts = Counter((row.monument_id, row.split) for row in first)
    for slug in cpu_config.canonical_monument_ids:
        assert counts[slug, "gallery"] == 8
        assert counts[slug, "calibration"] == 2
        assert counts[slug, "test"] == 2


def test_split_fails_when_a_class_is_below_minimum(cpu_config: MLConfig) -> None:
    rows = [
        _manifest_row(f"{slug}-{index}", slug, f"{slug}-{index}")
        for slug in cpu_config.canonical_monument_ids
        for index in range(11)
    ]
    with pytest.raises(ManifestError, match="at least 12"):
        assign_splits(rows, cpu_config)


def test_cross_split_hash_leakage_is_rejected() -> None:
    left = _manifest_row("left", "taj-mahal", "left", split="gallery")
    right = replace(
        _manifest_row("right", "taj-mahal", "right", split="test"),
        sha256=left.sha256,
    )
    with pytest.raises(ManifestError, match="cross-split leakage"):
        _check_leakage([left, right])


def test_same_split_near_duplicates_are_rejected() -> None:
    left = _manifest_row("left", "taj-mahal", "left", split="gallery")
    right = replace(
        _manifest_row("right", "taj-mahal", "right", split="gallery"),
        phash=left.phash,
    )
    with pytest.raises(ManifestError, match="accepted duplicate"):
        _check_leakage([left, right])


def test_manifest_csv_is_stable_and_handles_unicode(tmp_path: Path) -> None:
    path = tmp_path / "manifest.csv"
    row = replace(
        _manifest_row("stable", "taj-mahal", "stable", split="gallery"),
        author="Jos\u00e9, Example",
        attribution="Jos\u00e9, Example, CC BY 4.0",
    )
    write_manifest(path, [row])
    first = path.read_bytes()
    assert read_manifest(path) == (row,)
    write_manifest(path, [row])
    assert path.read_bytes() == first
