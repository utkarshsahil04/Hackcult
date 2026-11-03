"""Automated tests for demo cache, offline behavior, and network isolation (Issue #17)."""

from __future__ import annotations

import os

os.environ.setdefault("GEMINI_API_KEY", "test-key")

import hashlib
import socket
from pathlib import Path

from app.demo_cache import DemoCache, get_demo_cache
from app.main import app
from app.ml import get_pipeline
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = REPO_ROOT / "demo"
DEMO_IMAGES_DIR = DEMO_DIR / "images"

client = TestClient(app, raise_server_exceptions=False)

EXPECTED_DEMO_SLUGS = [
    "taj-mahal",
    "qutb-minar",
    "humayuns-tomb",
    "red-fort",
    "agra-fort",
]


def test_demo_photos_listing():
    """Verify GET /api/recognition/demo-photos returns all 5 demo photos."""
    response = client.get("/api/recognition/demo-photos")
    assert response.status_code == 200
    data = response.json()
    assert "photos" in data
    photos = data["photos"]
    assert len(photos) == 5

    slugs = [p["canonical_slug"] for p in photos]
    for expected_slug in EXPECTED_DEMO_SLUGS:
        assert expected_slug in slugs

    for p in photos:
        assert p["filename"].endswith(".jpg")
        assert len(p["sha256"]) == 64
        assert p["monument_name"]
        assert p["city"]


def test_demo_photo_retrieval_and_checksum():
    """Verify raw image retrieval and SHA-256 integrity for all 5 demo photos."""
    listing_resp = client.get("/api/recognition/demo-photos")
    assert listing_resp.status_code == 200
    photos = listing_resp.json()["photos"]

    for p in photos:
        # Retrieve by filename
        resp_fn = client.get(f"/api/recognition/demo-photos/{p['filename']}")
        assert resp_fn.status_code == 200
        assert resp_fn.headers["content-type"].startswith("image/jpeg")
        assert hashlib.sha256(resp_fn.content).hexdigest().lower() == p["sha256"].lower()

        # Retrieve by slug
        resp_slug = client.get(f"/api/recognition/demo-photos/{p['canonical_slug']}")
        assert resp_slug.status_code == 200
        assert resp_slug.content == resp_fn.content


def test_demo_photo_not_found():
    """Verify 404 error envelope when requesting a non-existent demo photo."""
    response = client.get("/api/recognition/demo-photos/nonexistent_monument.jpg")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "DEMO_PHOTO_NOT_FOUND"


def test_demo_photos_identify_cache_hit():
    """Verify all 5 demo photos hit the demo cache with status 'ok' and top candidate."""
    cache = get_demo_cache()
    pipeline = get_pipeline()
    status = pipeline.status()
    assert status.models in ("ok", "demo_cache")

    for slug in EXPECTED_DEMO_SLUGS:
        res = cache.get_photo_bytes(slug)
        assert res is not None, f"Missing demo photo file for {slug}"
        photo_bytes, _ = res

        response = client.post(
            "/api/recognition/identify",
            files={"photo": (f"{slug}.jpg", photo_bytes, "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert data.get("source") == "demo_cache"
        assert len(data["candidates"]) >= 1

        top_cand = data["candidates"][0]
        assert top_cand["slug"] == slug
        assert top_cand["score"] >= 0.85


def test_unknown_photo_never_hits_demo_cache():
    """Verify unknown photos return live_inference / uncertain and NEVER match demo cache."""
    # Create valid JPEG bytes that don't match any demo photo
    fake_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\xaa" * 200

    response = client.post(
        "/api/recognition/identify",
        files={"photo": ("unknown.jpg", fake_jpeg, "image/jpeg")},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "uncertain"
    assert data.get("source") == "live_inference"
    assert data["candidates"] == []


def test_demo_cache_graceful_missing_file(tmp_path):
    """Verify DemoCache handles non-existent or corrupted files without throwing."""
    missing_cache = DemoCache(cache_file=tmp_path / "does_not_exist.json")
    assert not missing_cache.has_entries()
    assert missing_cache.lookup_bytes(b"some bytes") is None
    assert not missing_cache.is_demo_photo(b"some bytes")
    assert missing_cache.list_photos() == []

    corrupted_file = tmp_path / "corrupt.json"
    corrupted_file.write_text("{not valid json", encoding="utf-8")
    corrupt_cache = DemoCache(cache_file=corrupted_file)
    assert not corrupt_cache.has_entries()


def test_full_offline_network_isolation(monkeypatch):
    """Verify end-to-end user tour succeeds when all external outbound calls are blocked."""
    orig_connect = socket.socket.connect

    def _blocked_external_connect(self, address):
        host = address[0] if isinstance(address, tuple) and address else address
        host_str = str(host).lower()
        if host_str in ("127.0.0.1", "localhost", "::1", "none", "0.0.0.0") or host_str.startswith("127."):
            return orig_connect(self, address)
        raise OSError(f"Offline isolation: external network access to {address!r} strictly forbidden")

    monkeypatch.setattr(socket.socket, "connect", _blocked_external_connect)

    # 1. Health check works offline
    health_resp = client.get("/api/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"

    # 2. Identify demo photo (Taj Mahal) works offline
    cache = get_demo_cache()
    photo_res = cache.get_photo_bytes("taj-mahal")
    assert photo_res is not None
    photo_bytes, _ = photo_res

    ident_resp = client.post(
        "/api/recognition/identify",
        files={"photo": ("taj_mahal.jpg", photo_bytes, "image/jpeg")},
    )
    assert ident_resp.status_code == 200
    assert ident_resp.json()["candidates"][0]["slug"] == "taj-mahal"

    # 3. Fetch monument details works offline
    monument_resp = client.get("/api/monuments/taj-mahal")
    assert monument_resp.status_code == 200
    assert monument_resp.json()["name"] == "Taj Mahal"

    # 4. Fetch grounded story works offline
    story_resp = client.get("/api/stories/taj-mahal?language=en&story_type=visitor")
    assert story_resp.status_code == 200
    assert "Taj Mahal" in story_resp.json()["body"]

    # 5. Nearby POIs work offline (precomputed Overpass cache)
    places_resp = client.get("/api/places/nearby?latitude=27.1751&longitude=78.0421&radius_m=3000")
    assert places_resp.status_code == 200
    assert len(places_resp.json()) > 0

    # 6. Tour planning works offline (precomputed ORS matrix + OR-Tools solver)
    plan_resp = client.post(
        "/api/tours/plan",
        json={
            "start_monument": "taj-mahal",
            "must_visit": ["agra-fort"],
            "max_stops": 3,
            "return_to_start": True,
            "time_budget_minutes": 360,
        },
    )
    assert plan_resp.status_code == 200
    plan_data = plan_resp.json()
    assert plan_data["itinerary"]["is_feasible"] is True
    assert len(plan_data["itinerary"]["stops"]) >= 2
