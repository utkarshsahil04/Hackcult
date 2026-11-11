import io
import json
import os

os.environ.setdefault("GEMINI_API_KEY", "test-key")

import sqlite3
from pathlib import Path

import pytest
from app.config import get_settings
from app.db import get_db
from app.main import app
from app.routes import archive
from fastapi.testclient import TestClient
from PIL import Image

SCHEMA = Path(__file__).resolve().parents[2] / "backend" / "app" / "db" / "schema.sql"
QUOTE = "Devanampiya Piyadasi says"


def _png(color=(200, 150, 90)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), color).save(buf, "PNG")
    return buf.getvalue()


class FakeGemini:
    def __init__(self, payload=None, fail=False):
        self.payload, self.fail, self.calls = payload, fail, 0

    def describe_image(self, *a, **k):
        self.calls += 1
        if self.fail:
            raise RuntimeError("boom")
        return json.dumps(self.payload)


GOOD = {
    "script": "Brahmi",
    "language": "Prakrit",
    "transcription": "DEVANAMPIYA PIYADASI LAJA HEVAM AHA",
    "translation_en": "Devanampiya  Piyadasi says: this is an edict.",
    "suggested_monument": "qutb-complex",
    "claims": [
        {"text": "An edict by Piyadasi.", "evidence_quote": "devanampiya piyadasi says"},
        {"text": "Invented fact.", "evidence_quote": "built in 1200 by a giant"},
    ],
}


@pytest.fixture
def env(tmp_path, monkeypatch):
    mon = sqlite3.connect(tmp_path / "m.db", check_same_thread=False)
    mon.row_factory = sqlite3.Row
    mon.executescript(SCHEMA.read_text(encoding="utf-8"))
    mon.execute(
        "INSERT INTO sources (id, source_key, url, title, publisher, source_type) VALUES (1,'s','https://a.example','T','P','government')"
    )
    for slug in ("qutb-complex", "taj-mahal"):
        mon.execute(
            "INSERT INTO monuments (slug, name, latitude, longitude, coordinates_source_id, era, architectural_style, location, city) "
            "VALUES (?, ?, 28.6, 77.2, 1, 'x', 'x', 'x', 'Delhi')",
            (slug, slug),
        )
    mon.commit()
    arch_path = tmp_path / "archive.db"

    def arch_db():
        conn = sqlite3.connect(arch_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.executescript(archive._SCHEMA)
        try:
            yield conn
        finally:
            conn.close()

    fake = FakeGemini(GOOD)
    app.dependency_overrides[get_db] = lambda: mon
    app.dependency_overrides[archive.get_archive_db] = arch_db
    app.dependency_overrides[archive.get_gemini] = lambda: fake
    archive._rate_store.clear()
    monkeypatch.setattr(get_settings(), "review_token", "secret")
    yield TestClient(app), fake
    app.dependency_overrides.clear()


def _post(client, data=None, rights="public-domain", mime="image/png", **extra):
    form = {"rights": rights, **extra} if rights else dict(extra)
    return client.post("/api/archive/digitise", files={"photo": ("a.png", data or _png(), mime)}, data=form)


def test_rights_required_and_checked(env):
    client, _ = env
    assert _post(client, rights=None).status_code == 400
    assert _post(client, rights="whatever").status_code == 400


def test_validation_errors(env):
    client, _ = env
    assert _post(client, mime="text/plain").status_code == 400
    assert _post(client, data=b"not an image").status_code == 400
    assert _post(client, data=b"\x00" * (6 * 1024 * 1024 + 1)).status_code == 400
    assert _post(client, monument_slug="nowhere").status_code == 400
    assert _post(client, source_note="x" * 301).status_code == 400


def test_evidence_filter_drops_invented_claims(env):
    client, _ = env
    r = _post(client)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "draft"
    assert [c["text"] for c in body["claims"]] == ["An edict by Piyadasi."]
    assert body["monument_slug"] == "qutb-complex"  # valid suggestion is kept as a draft guess
    assert client.get(body["image_url"]).headers["content-type"] == "image/jpeg"


def test_invalid_suggested_slug_is_dropped(env):
    client, fake = env
    fake.payload = {**GOOD, "suggested_monument": "atlantis"}
    assert _post(client).json()["monument_slug"] is None


def test_duplicate_image_returns_existing(env):
    client, fake = env
    first = _post(client).json()
    second = _post(client).json()
    assert first["id"] == second["id"] and fake.calls == 1


def test_gemini_failure_is_503(env):
    client, fake = env
    fake.fail = True
    r = _post(client)
    assert r.status_code == 503 and r.json()["error"]["code"] == "UPSTREAM_UNAVAILABLE"
    assert client.get("/api/archive/items").json()["items"] == []


def test_rate_limit(env):
    client, _ = env
    for i in range(20):
        assert _post(client, data=_png((i, 0, 0))).status_code == 200
    assert _post(client, data=_png((99, 9, 9))).status_code == 429


def test_review_auth_and_approved_only_on_monument(env, monkeypatch):
    client, _ = env
    item = _post(client).json()
    ids = [c["id"] for c in item["claims"]]
    body = {"claims": [{"id": ids[0], "decision": "approve", "text": "Edited text."}]}
    url = f"/api/archive/items/{item['id']}/review"

    assert client.post(url, json=body).status_code == 401
    assert client.post(url, json=body, headers={"X-Review-Token": "nope"}).status_code == 401
    assert client.get("/api/monuments/qutb-complex/archive").json()["items"] == []  # draft is invisible

    ok = client.post(url, json=body, headers={"X-Review-Token": "secret"})
    assert ok.status_code == 200 and ok.json()["status"] == "reviewed"
    shown = client.get("/api/monuments/qutb-complex/archive").json()["items"]
    assert [c["text"] for c in shown[0]["claims"]] == ["Edited text."]

    monkeypatch.setattr(get_settings(), "review_token", "")
    off = client.post(url, json=body, headers={"X-Review-Token": "secret"})
    assert off.status_code == 403 and off.json()["error"]["message"] == "Review is not enabled"


def test_rejected_claims_never_shown(env):
    client, _ = env
    item = _post(client).json()
    cid = item["claims"][0]["id"]
    r = client.post(
        f"/api/archive/items/{item['id']}/review",
        json={"claims": [{"id": cid, "decision": "reject"}], "monument_slug": "taj-mahal"},
        headers={"X-Review-Token": "secret"},
    )
    assert r.status_code == 200
    assert client.get("/api/monuments/taj-mahal/archive").json()["items"] == []
