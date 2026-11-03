"""Deterministic demo photo response cache for offline demonstrations (Issue #17)."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from app.ml import Candidate, PipelineResult

logger = logging.getLogger("raahein.api.demo_cache")

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_FILE = REPO_ROOT / "demo" / "cached_responses.json"
DEFAULT_IMAGES_DIR = REPO_ROOT / "demo" / "images"


class DemoCache:
    """Manages deterministic demo photo lookup by SHA-256 hash."""

    def __init__(self, cache_file: Path | None = None, images_dir: Path | None = None) -> None:
        self.cache_file = cache_file or DEFAULT_CACHE_FILE
        self.images_dir = images_dir or DEFAULT_IMAGES_DIR
        self._hash_to_photo: dict[str, dict[str, Any]] = {}
        self._slug_to_photo: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.cache_file.is_file():
            logger.info("Demo cache file not found at %s", self.cache_file)
            return
        try:
            raw = json.loads(self.cache_file.read_text(encoding="utf-8"))
            photos = raw.get("photos", [])
            for p in photos:
                sha = str(p.get("sha256", "")).lower()
                if sha:
                    self._hash_to_photo[sha] = p
                slug = p.get("canonical_slug")
                if slug:
                    self._slug_to_photo[slug] = p
                filename = p.get("filename")
                if filename:
                    self._slug_to_photo[filename] = p
            logger.info("Loaded %d demo photos from %s", len(photos), self.cache_file)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load demo cache from %s: %s", self.cache_file, exc)

    def has_entries(self) -> bool:
        return len(self._hash_to_photo) > 0

    def lookup_bytes(self, image_bytes: bytes) -> PipelineResult | None:
        """Deterministic lookup for raw image bytes using SHA-256."""
        if not self._hash_to_photo:
            return None

        sha = hashlib.sha256(image_bytes).hexdigest().lower()
        photo = self._hash_to_photo.get(sha)
        if not photo:
            return None

        res = photo.get("result", {})
        raw_candidates = res.get("candidates", [])
        candidates = [
            Candidate(
                slug=c["slug"],
                name=c["name"],
                score=float(c["score"]),
            )
            for c in raw_candidates
        ]
        return PipelineResult(
            status=res.get("status", "ok"),
            candidates=candidates,
            provenance="demo_cache",
        )

    def is_demo_photo(self, image_bytes: bytes) -> bool:
        sha = hashlib.sha256(image_bytes).hexdigest().lower()
        return sha in self._hash_to_photo

    def get_photo_bytes(self, identifier: str) -> tuple[bytes, str] | None:
        """Fetch raw bytes and media type for a demo photo by slug or filename."""
        photo = self._slug_to_photo.get(identifier)
        if not photo:
            # Check by filename inside images_dir
            target = self.images_dir / identifier
            if target.is_file():
                return target.read_bytes(), "image/jpeg"
            return None

        filename = photo.get("filename", "")
        target = self.images_dir / filename
        if not target.is_file():
            return None
        return target.read_bytes(), "image/jpeg"

    def list_photos(self) -> list[dict[str, Any]]:
        """List summary of all 5 demo photos."""
        items: list[dict[str, Any]] = []
        for p in self._hash_to_photo.values():
            items.append({
                "id": p.get("id"),
                "filename": p.get("filename"),
                "canonical_slug": p.get("canonical_slug"),
                "monument_name": p.get("monument_name"),
                "city": p.get("city"),
                "sha256": p.get("sha256"),
            })
        return items


_global_demo_cache: DemoCache | None = None


def get_demo_cache() -> DemoCache:
    global _global_demo_cache
    if _global_demo_cache is None:
        _global_demo_cache = DemoCache()
    return _global_demo_cache

