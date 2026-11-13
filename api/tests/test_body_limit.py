import os

os.environ.setdefault("GEMINI_API_KEY", "test-key")

from app.body_limit import MAX_BODY_BYTES
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)
URL = "/api/recognition/identify"


def _too_large(r):
    return r.status_code == 413 and r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_declared_oversized_body_is_refused_before_reading():
    r = client.post(URL, content=b"x" * (MAX_BODY_BYTES + 1), headers={"content-type": "multipart/form-data; boundary=b"})
    assert _too_large(r)


def test_chunked_body_without_length_is_cut_off():
    def chunks():
        for _ in range(MAX_BODY_BYTES // 65536 + 2):
            yield b"x" * 65536

    r = client.post(URL, content=chunks(), headers={"content-type": "multipart/form-data; boundary=b"})
    assert _too_large(r)


def test_small_bodies_still_reach_the_route():
    r = client.post("/api/tours/plan", json={"time_budget_minutes": 240, "time_limit_seconds": 11})
    assert r.status_code == 400  # the route's own validation answered, not the size cap
