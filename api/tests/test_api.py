import os

os.environ.setdefault("GEMINI_API_KEY", "test-key")

import sqlite3
from contextlib import closing

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


def test_health_reports_the_real_database_state(tmp_path, monkeypatch):
    database = lambda: client.get("/api/health").json()["subsystems"]["database"]  # noqa: E731

    monkeypatch.setattr("app.routes.health.resolve_db_path", lambda: tmp_path / "absent.db")
    assert database() == "missing"

    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"this is not a database")
    monkeypatch.setattr("app.routes.health.resolve_db_path", lambda: corrupt)
    assert database() == "error"

    good = tmp_path / "good.db"
    with closing(sqlite3.connect(good)) as conn:
        conn.execute("CREATE TABLE monuments (id INTEGER)")
        conn.commit()
    monkeypatch.setattr("app.routes.health.resolve_db_path", lambda: good)
    assert database() == "ok"


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