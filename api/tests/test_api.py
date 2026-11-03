import os

os.environ.setdefault("GEMINI_API_KEY", "test-key")

import pytest
from app.config import Settings
from app.main import app
from fastapi.testclient import TestClient
from pydantic import ValidationError


@app.get("/api/_boom")
def _boom():
    raise RuntimeError("boom")


client = TestClient(app, raise_server_exceptions=False)


def test_health_returns_200_with_subsystems():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert set(body["subsystems"]) == {"models", "faiss_index", "gemini", "database"}


def test_unknown_route_uses_error_envelope():
    r = client.get("/api/nope")
    assert r.status_code == 404
    err = r.json()["error"]
    assert err["code"] == "NOT_FOUND"
    assert err["message"] and err["hint"]


def test_wrong_method_uses_error_envelope():
    r = client.post("/api/health")
    assert r.status_code == 405
    assert r.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_unhandled_exception_becomes_500_envelope():
    r = client.get("/api/_boom")
    assert r.status_code == 500
    err = r.json()["error"]
    assert err["code"] == "INTERNAL_ERROR"
    assert "boom" not in r.text


def test_settings_fail_fast_on_empty_key():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, gemini_api_key="   ")