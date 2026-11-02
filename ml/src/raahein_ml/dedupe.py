"""Perceptual duplicate clustering and split-family construction."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from raahein_ml.config import semantic_hash
from raahein_ml.schemas import ArtifactError


@dataclass(frozen=True, slots=True)
class ImageFingerprint:
    image_id: str
    monument_id: str
    collection: str
    source_group: str
    sha256: str
    phash: str
    width: int
    height: int
    file_size_bytes: int
    eligible: bool = True


@dataclass(frozen=True, slots=True)
class ReviewPair:
    left_image_id: str
    left_monument_id: str
    right_image_id: str
    right_monument_id: str
    hamming_distance: int
    decision: str = ""
    reviewer: str = ""
    notes: str = ""

    @property
    def key(self) -> tuple[str, str]:
        return (self.left_image_id, self.right_image_id)


@dataclass(frozen=True, slots=True)
class DedupeOutcome:
    duplicate_group: str
    duplicate_of_image_id: str
    split_group: str
    status: str
    exclusion_reason: str


@dataclass(frozen=True, slots=True)
class DedupeResult:
    outcomes: Mapping[str, DedupeOutcome]
    review_pairs: tuple[ReviewPair, ...]

    @property
    def has_pending_review(self) -> bool:
        return any(not pair.decision for pair in self.review_pairs)


class _UnionFind:
    def __init__(self, keys: Iterable[str]) -> None:
        self.parent = {key: key for key in keys}

    def find(self, key: str) -> str:
        root = key
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[key] != key:
            parent = self.parent[key]
            self.parent[key] = root
            key = parent
        return root

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if left_root < right_root:
            self.parent[right_root] = left_root
        else:
            self.parent[left_root] = right_root

    def groups(self) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = defaultdict(list)
        for key in sorted(self.parent):
            grouped[self.find(key)].append(key)
        return grouped


def phash_hamming_distance(left: str, right: str) -> int:
    if len(left) != 16 or len(right) != 16:
        raise ValueError("64-bit perceptual hashes must contain 16 hexadecimal characters")
    try:
        return (int(left, 16) ^ int(right, 16)).bit_count()
    except ValueError as exc:
        raise ValueError("perceptual hashes must be hexadecimal") from exc


def _group_id(prefix: str, image_ids: Sequence[str]) -> str:
    return f"{prefix}-{semantic_hash(sorted(image_ids))[:16]}"


def _representative(records: Sequence[ImageFingerprint]) -> ImageFingerprint:
    return min(
        records,
        key=lambda row: (
            not row.eligible,
            -(row.width * row.height),
            -min(row.width, row.height),
            -row.file_size_bytes,
            row.image_id,
        ),
    )


def analyze_duplicates(
    records: Sequence[ImageFingerprint],
    existing_reviews: Mapping[tuple[str, str], ReviewPair] | None = None,
) -> DedupeResult:
    if not records:
        return DedupeResult(outcomes={}, review_pairs=())
    by_id = {row.image_id: row for row in records}
    if len(by_id) != len(records):
        raise ArtifactError("fingerprint image IDs must be unique")
    reviews = {} if existing_reviews is None else dict(existing_reviews)
    duplicate_families = _UnionFind(by_id)
    review_pairs: list[ReviewPair] = []
    pending_ids: set[str] = set()

    ordered = sorted(records, key=lambda row: row.image_id)
    for left_index, left in enumerate(ordered):
        for right in ordered[left_index + 1 :]:
            distance = phash_hamming_distance(left.phash, right.phash)
            if left.sha256 == right.sha256 or distance <= 4:
                duplicate_families.union(left.image_id, right.image_id)
                continue
            if not 5 <= distance <= 8:
                continue
            key = (left.image_id, right.image_id)
            review = reviews.get(key)
            review_is_current = review is not None and (
                review.left_monument_id == left.monument_id
                and review.right_monument_id == right.monument_id
                and review.hamming_distance == distance
            )
            decision = "" if not review_is_current else review.decision.strip().lower()
            if decision not in {"", "same", "different"}:
                raise ArtifactError(f"invalid duplicate review decision for {key}")
            candidate = ReviewPair(
                left_image_id=left.image_id,
                left_monument_id=left.monument_id,
                right_image_id=right.image_id,
                right_monument_id=right.monument_id,
                hamming_distance=distance,
                decision=decision,
                reviewer="" if not review_is_current else review.reviewer,
                notes="" if not review_is_current else review.notes,
            )
            review_pairs.append(candidate)
            if decision == "same":
                duplicate_families.union(left.image_id, right.image_id)
            elif not decision:
                pending_ids.update(key)

    clusters = duplicate_families.groups()
    cluster_by_id: dict[str, list[str]] = {}
    for image_ids in clusters.values():
        for image_id in image_ids:
            cluster_by_id[image_id] = image_ids

    split_families = _UnionFind(by_id)
    for image_ids in clusters.values():
        first = image_ids[0]
        for image_id in image_ids[1:]:
            split_families.union(first, image_id)
    source_groups: dict[str, list[str]] = defaultdict(list)
    for row in records:
        source_groups[row.source_group].append(row.image_id)
    for image_ids in source_groups.values():
        first = image_ids[0]
        for image_id in image_ids[1:]:
            split_families.union(first, image_id)
    split_clusters = split_families.groups()
    split_group_by_id: dict[str, str] = {}
    for image_ids in split_clusters.values():
        split_group = _group_id("split", image_ids)
        for image_id in image_ids:
            split_group_by_id[image_id] = split_group

    outcomes: dict[str, DedupeOutcome] = {}
    processed: set[str] = set()
    for image_id in sorted(by_id):
        if image_id in processed:
            continue
        image_ids = cluster_by_id[image_id]
        processed.update(image_ids)
        members = [by_id[member_id] for member_id in image_ids]
        duplicate_group = _group_id("dup", image_ids)
        monument_ids = {member.monument_id for member in members}
        collections = {member.collection for member in members}
        if len(monument_ids) > 1:
            for member in members:
                outcomes[member.image_id] = DedupeOutcome(
                    duplicate_group=duplicate_group,
                    duplicate_of_image_id="",
                    split_group=split_group_by_id[member.image_id],
                    status="quarantined",
                    exclusion_reason="cross_label_duplicate",
                )
            continue
        if len(collections) > 1:
            for member in members:
                outcomes[member.image_id] = DedupeOutcome(
                    duplicate_group=duplicate_group,
                    duplicate_of_image_id="",
                    split_group=split_group_by_id[member.image_id],
                    status="quarantined",
                    exclusion_reason="cross_collection_duplicate",
                )
            continue
        representative = _representative(members)
        for member in members:
            if member.image_id in pending_ids:
                status = "quarantined"
                reason = "manual_review_pending"
                duplicate_of = ""
            elif member.image_id == representative.image_id:
                status = "accepted"
                reason = ""
                duplicate_of = ""
            else:
                status = "excluded"
                reason = "inferior_duplicate"
                duplicate_of = representative.image_id
            outcomes[member.image_id] = DedupeOutcome(
                duplicate_group=duplicate_group,
                duplicate_of_image_id=duplicate_of,
                split_group=split_group_by_id[member.image_id],
                status=status,
                exclusion_reason=reason,
            )
    return DedupeResult(
        outcomes=outcomes,
        review_pairs=tuple(sorted(review_pairs, key=lambda pair: pair.key)),
    )
