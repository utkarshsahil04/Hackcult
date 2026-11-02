"""Licensed source ingestion, image analysis, splitting, and manifest validation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import warnings
from collections import Counter, defaultdict
from contextlib import suppress
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

import httpx
import numpy as np
from ortools.sat.python import cp_model
from PIL import Image, UnidentifiedImageError

from raahein_ml.config import (
    MLConfig,
    canonical_json_bytes,
    load_config,
    semantic_hash,
    sha256_file,
)
from raahein_ml.dedupe import (
    DedupeResult,
    ImageFingerprint,
    ReviewPair,
    analyze_duplicates,
    phash_hamming_distance,
)
from raahein_ml.images import prepare_rgb_image
from raahein_ml.schemas import ConfigurationError

SOURCE_FIELDS = (
    "source_id",
    "collection",
    "monument_id",
    "component",
    "source_page_url",
    "download_url",
    "author",
    "license_id",
    "license_url",
    "attribution",
    "source_group",
)
MANIFEST_FIELDS = (
    "image_id",
    "source_id",
    "collection",
    "monument_id",
    "component",
    "local_path",
    "source_group",
    "source_page_url",
    "download_url",
    "author",
    "license_id",
    "license_url",
    "attribution",
    "image_format",
    "width",
    "height",
    "file_size_bytes",
    "sha256",
    "phash",
    "duplicate_group",
    "duplicate_of_image_id",
    "split_group",
    "status",
    "exclusion_reason",
    "split",
)
REVIEW_FIELDS = (
    "left_image_id",
    "left_monument_id",
    "right_image_id",
    "right_monument_id",
    "hamming_distance",
    "decision",
    "reviewer",
    "notes",
)
NEGATIVE_FIELDS = (
    "image_id",
    "category",
    "local_path",
    "source_id",
    "source_page_url",
    "download_url",
    "author",
    "license_id",
    "license_url",
    "attribution",
    "sha256",
    "phash",
)

ALLOWED_LICENSES = frozenset(
    {
        "LicenseRef-Public-Domain",
        "CC0-1.0",
        "CC-BY-1.0",
        "CC-BY-2.0",
        "CC-BY-2.5",
        "CC-BY-3.0",
        "CC-BY-4.0",
        "CC-BY-SA-1.0",
        "CC-BY-SA-2.0",
        "CC-BY-SA-2.5",
        "CC-BY-SA-3.0",
        "CC-BY-SA-4.0",
    }
)
EXCLUSION_REASONS = frozenset(
    {
        "",
        "corrupt_image",
        "decompression_bomb",
        "too_small",
        "animated_image",
        "inferior_duplicate",
        "cross_label_duplicate",
        "cross_collection_duplicate",
        "manual_review_pending",
    }
)
STOCK_HOST_FRAGMENTS = (
    "alamy.",
    "dreamstime.",
    "gettyimages.",
    "istockphoto.",
    "pinterest.",
    "shutterstock.",
    "stock.adobe.",
)
SAFE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
MINIMUM_IMAGE_SIDE = 224
MAXIMUM_DOWNLOAD_BYTES = 50 * 1024 * 1024


class ManifestError(ValueError):
    """A source, image, split, or manifest violates the curation contract."""


class ImageRejected(ManifestError):
    def __init__(
        self,
        reason: str,
        *,
        image_sha256: str,
        file_size_bytes: int,
    ) -> None:
        super().__init__(reason)
        self.reason = reason
        self.image_sha256 = image_sha256
        self.file_size_bytes = file_size_bytes


@dataclass(frozen=True, slots=True)
class SourceRecord:
    source_id: str
    collection: str
    monument_id: str
    component: str
    source_page_url: str
    download_url: str
    author: str
    license_id: str
    license_url: str
    attribution: str
    source_group: str

    @property
    def local_path(self) -> str:
        return (PurePosixPath("data") / "raw" / self.source_id).as_posix()


@dataclass(frozen=True, slots=True)
class ImageAnalysis:
    image_format: str
    width: int
    height: int
    file_size_bytes: int
    sha256: str
    phash: str


@dataclass(frozen=True, slots=True)
class ManifestRow:
    image_id: str
    source_id: str
    collection: str
    monument_id: str
    component: str
    local_path: str
    source_group: str
    source_page_url: str
    download_url: str
    author: str
    license_id: str
    license_url: str
    attribution: str
    image_format: str
    width: int | None
    height: int | None
    file_size_bytes: int | None
    sha256: str
    phash: str
    duplicate_group: str = ""
    duplicate_of_image_id: str = ""
    split_group: str = ""
    status: str = "accepted"
    exclusion_reason: str = ""
    split: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            field: "" if getattr(self, field) is None else getattr(self, field)
            for field in MANIFEST_FIELDS
        }

    @classmethod
    def from_dict(cls, raw: dict[str, str]) -> ManifestRow:
        def optional_int(name: str) -> int | None:
            value = raw[name].strip()
            return None if not value else int(value)

        try:
            return cls(
                **{
                    **{name: raw[name].strip() for name in MANIFEST_FIELDS},
                    "width": optional_int("width"),
                    "height": optional_int("height"),
                    "file_size_bytes": optional_int("file_size_bytes"),
                }
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ManifestError("manifest row has invalid fields") from exc


def validate_provenance_url(value: str, field: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ManifestError(f"{field} must be a traceable HTTPS URL")
    hostname = (parsed.hostname or "").lower()
    if any(fragment in hostname for fragment in STOCK_HOST_FRAGMENTS):
        raise ManifestError(f"{field} points to a disallowed stock/search host")


def validate_source(source: SourceRecord, canonical_ids: set[str]) -> None:
    if not SAFE_ID_PATTERN.fullmatch(source.source_id):
        raise ManifestError(f"unsafe source_id: {source.source_id}")
    if source.collection not in {"curated", "independent"}:
        raise ManifestError(f"invalid collection for {source.source_id}")
    if source.monument_id not in canonical_ids:
        raise ManifestError(f"non-canonical monument ID for {source.source_id}")
    if not SAFE_ID_PATTERN.fullmatch(source.source_group):
        raise ManifestError(f"unsafe source_group for {source.source_id}")
    validate_provenance_url(source.source_page_url, "source_page_url")
    validate_provenance_url(source.download_url, "download_url")
    validate_provenance_url(source.license_url, "license_url")
    if source.license_id not in ALLOWED_LICENSES:
        raise ManifestError(f"disallowed licence for {source.source_id}: {source.license_id}")
    if not source.author.strip() or not source.attribution.strip():
        raise ManifestError(f"incomplete attribution for {source.source_id}")


def _read_dict_rows(path: Path, fields: tuple[str, ...]) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != fields:
                raise ManifestError(f"{path} has an unexpected CSV header")
            return [dict(row) for row in reader]
    except OSError as exc:
        raise ManifestError(f"cannot read {path}") from exc


def read_sources(path: Path, canonical_ids: tuple[str, ...]) -> tuple[SourceRecord, ...]:
    rows = _read_dict_rows(path, SOURCE_FIELDS)
    sources: list[SourceRecord] = []
    seen: set[str] = set()
    canonical = set(canonical_ids)
    for raw in rows:
        source = SourceRecord(**{field: (raw[field] or "").strip() for field in SOURCE_FIELDS})
        folded = source.source_id.casefold()
        if folded in seen:
            raise ManifestError(f"duplicate source_id: {source.source_id}")
        seen.add(folded)
        validate_source(source, canonical)
        sources.append(source)
    return tuple(sorted(sources, key=lambda source: source.source_id))


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


def _csv_payload(fields: tuple[str, ...], rows: list[dict[str, object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def write_manifest(path: Path, rows: list[ManifestRow]) -> None:
    ordered = sorted(rows, key=lambda row: row.image_id)
    _atomic_write(path, _csv_payload(MANIFEST_FIELDS, [row.to_dict() for row in ordered]))


def read_manifest(path: Path) -> tuple[ManifestRow, ...]:
    rows = _read_dict_rows(path, MANIFEST_FIELDS)
    parsed = tuple(ManifestRow.from_dict(row) for row in rows)
    if list(parsed) != sorted(parsed, key=lambda row: row.image_id):
        raise ManifestError(f"{path} rows must be sorted by image_id")
    if len({row.image_id for row in parsed}) != len(parsed):
        raise ManifestError(f"{path} contains duplicate image IDs")
    return parsed


def read_reviews(path: Path) -> dict[tuple[str, str], ReviewPair]:
    rows = _read_dict_rows(path, REVIEW_FIELDS)
    reviews: dict[tuple[str, str], ReviewPair] = {}
    for raw in rows:
        try:
            pair = ReviewPair(
                left_image_id=raw["left_image_id"].strip(),
                left_monument_id=raw["left_monument_id"].strip(),
                right_image_id=raw["right_image_id"].strip(),
                right_monument_id=raw["right_monument_id"].strip(),
                hamming_distance=int(raw["hamming_distance"]),
                decision=raw["decision"].strip().lower(),
                reviewer=raw["reviewer"].strip(),
                notes=raw["notes"].strip(),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ManifestError("duplicate review row is invalid") from exc
        if pair.left_image_id >= pair.right_image_id:
            raise ManifestError("duplicate review pair IDs must be lexically ordered")
        if pair.decision not in {"", "same", "different"}:
            raise ManifestError("duplicate review decision must be blank, same, or different")
        if pair.decision and not pair.reviewer:
            raise ManifestError("completed duplicate reviews require a reviewer")
        if pair.key in reviews:
            raise ManifestError(f"duplicate review pair: {pair.key}")
        reviews[pair.key] = pair
    return reviews


def write_reviews(path: Path, reviews: tuple[ReviewPair, ...]) -> None:
    rows = [
        {field: getattr(review, field) for field in REVIEW_FIELDS}
        for review in sorted(reviews, key=lambda pair: pair.key)
    ]
    _atomic_write(path, _csv_payload(REVIEW_FIELDS, rows))


def _perceptual_hash(image: Image.Image) -> str:
    size = 32
    pixels = np.asarray(
        image.convert("L").resize((size, size), Image.Resampling.LANCZOS), dtype=np.float64
    )
    positions = np.arange(size, dtype=np.float64)
    frequencies = positions.reshape(-1, 1)
    # Match scipy.fftpack.dct's unnormalized DCT-II used by the reference pHash.
    transform = 2 * np.cos(np.pi * (positions + 0.5) * frequencies / size)
    low_frequency = (transform @ pixels @ transform.T)[:8, :8]
    median = float(np.median(low_frequency))
    bits = (low_frequency > median).reshape(-1)
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return f"{value:016x}"


def analyze_image(path: Path) -> ImageAnalysis:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ManifestError(f"cannot read local image: {path}") from exc
    image_sha256 = hashlib.sha256(payload).hexdigest()
    file_size = len(payload)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(payload)) as probe:
                image_format = (probe.format or "unknown").lower()
                if getattr(probe, "n_frames", 1) != 1:
                    raise ImageRejected(
                        "animated_image",
                        image_sha256=image_sha256,
                        file_size_bytes=file_size,
                    )
                probe.verify()
            with Image.open(io.BytesIO(payload)) as decoded:
                decoded.load()
                rgb = prepare_rgb_image(decoded)
                width, height = rgb.size
                phash = _perceptual_hash(rgb)
    except ImageRejected:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageRejected(
            "decompression_bomb",
            image_sha256=image_sha256,
            file_size_bytes=file_size,
        ) from exc
    except (OSError, SyntaxError, UnidentifiedImageError, ValueError) as exc:
        raise ImageRejected(
            "corrupt_image",
            image_sha256=image_sha256,
            file_size_bytes=file_size,
        ) from exc
    return ImageAnalysis(
        image_format=image_format,
        width=width,
        height=height,
        file_size_bytes=file_size,
        sha256=image_sha256,
        phash=phash,
    )


def _row_from_source(source: SourceRecord, repository_root: Path) -> ManifestRow:
    path = repository_root / PurePosixPath(source.local_path)
    if not path.is_file():
        raise ManifestError(f"missing downloaded image for {source.source_id}: {path}")
    base: dict[str, Any] = {
        "image_id": source.source_id,
        "source_id": source.source_id,
        "collection": source.collection,
        "monument_id": source.monument_id,
        "component": source.component,
        "local_path": source.local_path,
        "source_group": source.source_group,
        "source_page_url": source.source_page_url,
        "download_url": source.download_url,
        "author": source.author,
        "license_id": source.license_id,
        "license_url": source.license_url,
        "attribution": source.attribution,
    }
    try:
        analysis = analyze_image(path)
    except ImageRejected as exc:
        return ManifestRow(
            **base,
            image_format="",
            width=None,
            height=None,
            file_size_bytes=exc.file_size_bytes,
            sha256=exc.image_sha256,
            phash="",
            status="quarantined",
            exclusion_reason=exc.reason,
        )
    too_small = min(analysis.width, analysis.height) < MINIMUM_IMAGE_SIDE
    return ManifestRow(
        **base,
        image_format=analysis.image_format,
        width=analysis.width,
        height=analysis.height,
        file_size_bytes=analysis.file_size_bytes,
        sha256=analysis.sha256,
        phash=analysis.phash,
        status="quarantined" if too_small else "accepted",
        exclusion_reason="too_small" if too_small else "",
    )


def _fingerprint(row: ManifestRow) -> ImageFingerprint:
    if row.width is None or row.height is None or row.file_size_bytes is None or not row.phash:
        raise ManifestError(f"{row.image_id} has no decoded fingerprint")
    return ImageFingerprint(
        image_id=row.image_id,
        monument_id=row.monument_id,
        collection=row.collection,
        source_group=row.source_group,
        sha256=row.sha256,
        phash=row.phash,
        width=row.width,
        height=row.height,
        file_size_bytes=row.file_size_bytes,
        eligible=row.status == "accepted",
    )


def _apply_dedupe(rows: list[ManifestRow], result: DedupeResult) -> list[ManifestRow]:
    updated: list[ManifestRow] = []
    for row in rows:
        outcome = result.outcomes.get(row.image_id)
        if outcome is None:
            updated.append(row)
            continue
        preserve_decode_quarantine = row.exclusion_reason in {
            "corrupt_image",
            "decompression_bomb",
            "too_small",
            "animated_image",
        }
        updated.append(
            replace(
                row,
                duplicate_group=outcome.duplicate_group,
                duplicate_of_image_id=(
                    row.duplicate_of_image_id
                    if preserve_decode_quarantine
                    else outcome.duplicate_of_image_id
                ),
                split_group=outcome.split_group,
                status=row.status if preserve_decode_quarantine else outcome.status,
                exclusion_reason=(
                    row.exclusion_reason if preserve_decode_quarantine else outcome.exclusion_reason
                ),
            )
        )
    return updated


def _new_solver() -> cp_model.CpSolver:
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    return solver


def assign_splits(rows: list[ManifestRow], config: MLConfig) -> list[ManifestRow]:
    accepted = [
        row for row in rows if row.collection == "curated" and row.status == "accepted"
    ]
    if not accepted:
        raise ManifestError("no accepted curated images are available for splitting")
    if any(not row.split_group for row in accepted):
        raise ManifestError("accepted images require a split group")
    canonical = config.canonical_monument_ids
    groups: dict[str, list[ManifestRow]] = defaultdict(list)
    for row in accepted:
        groups[row.split_group].append(row)
    group_names = sorted(groups)
    counts = {
        group: Counter(row.monument_id for row in members) for group, members in groups.items()
    }
    total_by_class = Counter(row.monument_id for row in accepted)
    if set(total_by_class) != set(canonical):
        raise ManifestError("accepted corpus must contain every canonical monument")
    required = (
        config.split.minimum_gallery
        + config.split.calibration_per_class
        + config.split.test_per_class
    )
    if min(total_by_class.values()) < required:
        raise ManifestError(f"every class needs at least {required} accepted images")

    roles = ("gallery", "calibration", "test", "reserve")
    model = cp_model.CpModel()
    variables = {
        (group, role): model.NewBoolVar(f"assign_{index}_{role}")
        for index, group in enumerate(group_names)
        for role in roles
    }
    gallery_count = model.NewIntVar(
        config.split.minimum_gallery,
        config.split.maximum_gallery,
        "gallery_count",
    )
    for group in group_names:
        model.Add(sum(variables[group, role] for role in roles) == 1)
    for monument_id in canonical:
        calibration_total = sum(
            counts[group][monument_id] * variables[group, "calibration"]
            for group in group_names
        )
        test_total_for_class = sum(
            counts[group][monument_id] * variables[group, "test"] for group in group_names
        )
        gallery_total = sum(
            counts[group][monument_id] * variables[group, "gallery"]
            for group in group_names
        )
        model.Add(calibration_total == config.split.calibration_per_class)
        model.Add(test_total_for_class >= config.split.test_per_class)
        model.Add(gallery_total == gallery_count)

    total_test = sum(
        sum(counts[group].values()) * variables[group, "test"] for group in group_names
    )
    model.Minimize(total_test)
    solver = _new_solver()
    if solver.Solve(model) != cp_model.OPTIMAL:
        raise ManifestError("no optimal leakage-safe split satisfies the class quotas")
    optimal_test = solver.Value(total_test)
    model.Add(total_test == optimal_test)

    model.Maximize(gallery_count)
    solver = _new_solver()
    if solver.Solve(model) != cp_model.OPTIMAL:
        raise ManifestError("failed to maximize the balanced gallery")
    optimal_gallery = solver.Value(gallery_count)
    model.Add(gallery_count == optimal_gallery)

    role_rank = {role: index for index, role in enumerate(roles, start=1)}
    stable_cost = sum(
        (int(hashlib.sha256(group.encode()).hexdigest()[:8], 16) + 1)
        * role_rank[role]
        * variables[group, role]
        for group in group_names
        for role in roles
    )
    model.Minimize(stable_cost)
    solver = _new_solver()
    if solver.Solve(model) != cp_model.OPTIMAL:
        raise ManifestError("failed to select a deterministic optimal split")

    role_by_group: dict[str, str] = {}
    for group in group_names:
        selected = [role for role in roles if solver.Value(variables[group, role])]
        if len(selected) != 1:
            raise ManifestError("split solver returned an invalid group assignment")
        role_by_group[group] = selected[0]

    split_rows = [
        replace(row, split=role_by_group[row.split_group])
        if row.collection == "curated" and row.status == "accepted"
        else row
        for row in rows
    ]
    accepted_split = [
        row
        for row in split_rows
        if row.collection == "curated" and row.status == "accepted"
    ]
    gallery_counts = Counter(
        row.monument_id for row in accepted_split if row.split == "gallery"
    )
    calibration_counts = Counter(
        row.monument_id for row in accepted_split if row.split == "calibration"
    )
    test_counts = Counter(row.monument_id for row in accepted_split if row.split == "test")
    if set(gallery_counts.values()) != {optimal_gallery}:
        raise ManifestError("gallery is not balanced after solving")
    if any(calibration_counts[slug] != config.split.calibration_per_class for slug in canonical):
        raise ManifestError("calibration quotas changed after solving")
    if any(test_counts[slug] < config.split.test_per_class for slug in canonical):
        raise ManifestError("test quotas changed after solving")
    eligible_gallery = min(
        total_by_class[slug] - calibration_counts[slug] - test_counts[slug]
        for slug in canonical
    )
    prescribed_gallery = min(config.split.maximum_gallery, eligible_gallery)
    if optimal_gallery != prescribed_gallery:
        raise ManifestError("group constraints prevent the prescribed balanced gallery size")
    return split_rows


def _validate_relative_local_path(row: ManifestRow, repository_root: Path) -> Path:
    pure = PurePosixPath(row.local_path)
    if pure.is_absolute() or ".." in pure.parts or pure.parts[:2] != ("data", "raw"):
        raise ManifestError(f"unsafe local path for {row.image_id}")
    resolved = (repository_root / Path(*pure.parts)).resolve()
    try:
        resolved.relative_to(repository_root)
    except ValueError as exc:
        raise ManifestError(f"local path escapes repository for {row.image_id}") from exc
    return resolved


def _validate_row(row: ManifestRow, config: MLConfig) -> None:
    if row.image_id != row.source_id or not SAFE_ID_PATTERN.fullmatch(row.image_id):
        raise ManifestError(f"invalid image/source ID for {row.image_id}")
    if row.monument_id not in set(config.canonical_monument_ids):
        raise ManifestError(f"non-canonical label for {row.image_id}")
    if row.license_id not in ALLOWED_LICENSES:
        raise ManifestError(f"disallowed licence for {row.image_id}")
    if not row.author or not row.attribution:
        raise ManifestError(f"missing provenance for {row.image_id}")
    validate_provenance_url(row.source_page_url, "source_page_url")
    validate_provenance_url(row.download_url, "download_url")
    validate_provenance_url(row.license_url, "license_url")
    _validate_relative_local_path(row, config.repository_root)
    if row.status not in {"accepted", "excluded", "quarantined"}:
        raise ManifestError(f"invalid status for {row.image_id}")
    if row.exclusion_reason not in EXCLUSION_REASONS:
        raise ManifestError(f"invalid exclusion reason for {row.image_id}")
    if row.status == "accepted" and row.exclusion_reason:
        raise ManifestError(f"accepted row has an exclusion reason: {row.image_id}")
    if row.status != "accepted" and not row.exclusion_reason:
        raise ManifestError(f"non-accepted row lacks an exclusion reason: {row.image_id}")
    if row.status == "accepted":
        if not all(
            (
                row.image_format,
                row.width,
                row.height,
                row.file_size_bytes,
                row.sha256,
                row.phash,
                row.duplicate_group,
                row.split_group,
            )
        ):
            raise ManifestError(f"accepted row is incomplete: {row.image_id}")
        if min(int(row.width), int(row.height)) < MINIMUM_IMAGE_SIDE:
            raise ManifestError(f"accepted image is too small: {row.image_id}")


def _check_leakage(rows: list[ManifestRow]) -> None:
    accepted = [row for row in rows if row.status == "accepted"]
    for left_index, left in enumerate(accepted):
        for right in accepted[left_index + 1 :]:
            reasons: list[str] = []
            if left.sha256 == right.sha256:
                reasons.append("SHA-256")
            if phash_hamming_distance(left.phash, right.phash) <= 4:
                reasons.append("pHash")
            if left.split == right.split:
                if reasons:
                    joined = ", ".join(reasons)
                    raise ManifestError(
                        f"accepted duplicate {left.image_id}/{right.image_id}: {joined}"
                    )
                continue
            for field in (
                "source_group",
                "duplicate_group",
                "split_group",
                "source_page_url",
                "download_url",
            ):
                if getattr(left, field) == getattr(right, field):
                    reasons.append(field)
            if reasons:
                joined = ", ".join(reasons)
                raise ManifestError(
                    f"cross-split leakage between {left.image_id} and {right.image_id}: {joined}"
                )


def validate_manifests(
    manifest_rows: list[ManifestRow],
    independent_rows: list[ManifestRow],
    config: MLConfig,
    *,
    rehash: bool = False,
    require_independent_count: bool = True,
) -> None:
    rows = manifest_rows + independent_rows
    if len({row.image_id.casefold() for row in rows}) != len(rows):
        raise ManifestError("image IDs must be unique across all positive manifests")
    for row in rows:
        _validate_row(row, config)
        if rehash and row.status == "accepted":
            analysis = analyze_image(_validate_relative_local_path(row, config.repository_root))
            recorded = (
                row.image_format,
                row.width,
                row.height,
                row.file_size_bytes,
                row.sha256,
                row.phash,
            )
            observed = (
                analysis.image_format,
                analysis.width,
                analysis.height,
                analysis.file_size_bytes,
                analysis.sha256,
                analysis.phash,
            )
            if recorded != observed:
                raise ManifestError(f"recorded fingerprint differs for {row.image_id}")

    curated = [
        row for row in manifest_rows if row.collection == "curated" and row.status == "accepted"
    ]
    if any(row.collection != "curated" for row in manifest_rows):
        raise ManifestError("main manifest may contain only curated rows")
    if any(row.split not in {"gallery", "calibration", "test", "reserve"} for row in curated):
        raise ManifestError("accepted curated rows require a valid split")
    canonical = set(config.canonical_monument_ids)
    if {row.monument_id for row in curated} != canonical:
        raise ManifestError("accepted curated rows do not cover all canonical monuments")
    gallery_counts = Counter(row.monument_id for row in curated if row.split == "gallery")
    calibration_counts = Counter(
        row.monument_id for row in curated if row.split == "calibration"
    )
    test_counts = Counter(row.monument_id for row in curated if row.split == "test")
    if set(gallery_counts) != canonical or len(set(gallery_counts.values())) != 1:
        raise ManifestError("gallery must be balanced across all canonical monuments")
    gallery_size = next(iter(gallery_counts.values()))
    if not config.split.minimum_gallery <= gallery_size <= config.split.maximum_gallery:
        raise ManifestError("gallery size is outside the configured bounds")
    if any(calibration_counts[slug] != config.split.calibration_per_class for slug in canonical):
        raise ManifestError("each monument requires exactly two calibration images")
    if any(test_counts[slug] < config.split.test_per_class for slug in canonical):
        raise ManifestError("each monument requires at least two final-test images")

    independent = [row for row in independent_rows if row.status == "accepted"]
    if any(row.collection != "independent" for row in independent_rows):
        raise ManifestError("independent manifest may contain only independent rows")
    if any(row.split != "independent_test" for row in independent):
        raise ManifestError("accepted independent rows require the independent_test split")
    if require_independent_count:
        if len(independent) != config.evaluation.independent_positive_count:
            raise ManifestError(
                "independent set requires exactly "
                f"{config.evaluation.independent_positive_count} images"
            )
        if {row.monument_id for row in independent} != canonical:
            raise ManifestError("independent set must represent all canonical monuments")
    _check_leakage(rows)


def _scan_sources(
    sources: tuple[SourceRecord, ...],
    config: MLConfig,
    review_path: Path,
) -> tuple[list[ManifestRow], DedupeResult]:
    rows = [_row_from_source(source, config.repository_root) for source in sources]
    reviews = read_reviews(review_path)
    fingerprints = [
        _fingerprint(row)
        for row in rows
        if row.width is not None and row.height is not None and row.phash
    ]
    result = analyze_duplicates(fingerprints, reviews)
    write_reviews(review_path, result.review_pairs)
    return _apply_dedupe(rows, result), result


def fetch_sources(sources: tuple[SourceRecord, ...], repository_root: Path) -> None:
    if not sources:
        raise ManifestError("source catalogue is empty")
    with httpx.Client(follow_redirects=True, timeout=30.0) as client:
        for source in sources:
            destination = repository_root / PurePosixPath(source.local_path)
            receipt_path = (
                repository_root
                / "data"
                / "cache"
                / "download_receipts"
                / f"{source.source_id}.json"
            )
            source_contract = semantic_hash(
                {field: getattr(source, field) for field in SOURCE_FIELDS}
            )
            if destination.is_file() and receipt_path.is_file():
                try:
                    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                    if (
                        receipt.get("source_contract") == source_contract
                        and receipt.get("sha256") == sha256_file(destination)
                    ):
                        continue
                except (OSError, json.JSONDecodeError):
                    pass
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                with client.stream("GET", source.download_url) as response:
                    response.raise_for_status()
                    if not str(response.url).startswith("https://"):
                        raise ManifestError(
                            f"download redirected away from HTTPS: {source.source_id}"
                        )
                    content_type = response.headers.get("content-type", "").split(";", 1)[0]
                    if not content_type.startswith("image/"):
                        raise ManifestError(f"download is not an image: {source.source_id}")
                    chunks: list[bytes] = []
                    size = 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > MAXIMUM_DOWNLOAD_BYTES:
                            raise ManifestError(f"download is too large: {source.source_id}")
                        chunks.append(chunk)
            except httpx.HTTPError as exc:
                raise ManifestError(f"download failed for {source.source_id}") from exc
            payload = b"".join(chunks)
            _atomic_write(destination, payload)
            _atomic_write(
                receipt_path,
                canonical_json_bytes(
                    {
                        "source_contract": source_contract,
                        "sha256": hashlib.sha256(payload).hexdigest(),
                    }
                )
                + b"\n",
            )


def scan(config: MLConfig, *, build: bool) -> None:
    sources = read_sources(config.paths.source_catalog, config.canonical_monument_ids)
    if not sources:
        raise ManifestError("source catalogue is empty")
    review_path = config.paths.manifest.parent / "duplicate_review.csv"
    rows, dedupe_result = _scan_sources(sources, config, review_path)
    if build and dedupe_result.has_pending_review:
        raise ManifestError("manual duplicate review is incomplete")
    if build:
        rows = assign_splits(rows, config)
    rows = [
        replace(row, split="independent_test")
        if row.collection == "independent" and row.status == "accepted"
        else row
        for row in rows
    ]
    curated = [row for row in rows if row.collection == "curated"]
    independent = [row for row in rows if row.collection == "independent"]
    if build:
        validate_manifests(curated, independent, config, rehash=True)
        write_manifest(config.paths.manifest, curated)
        write_manifest(config.paths.manifest.parent / "independent_test.csv", independent)
    else:
        draft_root = config.paths.embedding_cache.parent
        write_manifest(draft_root / "manifest_scan.csv", curated)
        write_manifest(draft_root / "independent_scan.csv", independent)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="path to models.yaml")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("fetch", help="download validated licensed sources")
    subparsers.add_parser("scan", help="analyze images and refresh duplicate review")
    subparsers.add_parser("build", help="build and strictly validate final splits")
    validate = subparsers.add_parser("validate", help="validate tracked manifests")
    validate.add_argument("--rehash", action="store_true", help="recompute image fingerprints")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        if args.command == "fetch":
            sources = read_sources(config.paths.source_catalog, config.canonical_monument_ids)
            fetch_sources(sources, config.repository_root)
        elif args.command == "scan":
            scan(config, build=False)
        elif args.command == "build":
            scan(config, build=True)
        else:
            manifest_rows = list(read_manifest(config.paths.manifest))
            independent_rows = list(
                read_manifest(config.paths.manifest.parent / "independent_test.csv")
            )
            validate_manifests(
                manifest_rows,
                independent_rows,
                config,
                rehash=args.rehash,
            )
    except (ConfigurationError, ManifestError) as exc:
        print(f"manifest error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
