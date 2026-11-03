import os

os.environ.setdefault("GEMINI_API_KEY", "test-key")

import sqlite3
from pathlib import Path

import pytest
from app.db import get_db
from app.main import app
from fastapi.testclient import TestClient

SCHEMA = Path(__file__).resolve().parents[2] / "backend" / "app" / "db" / "schema.sql"


def _monument(conn, slug, name):
    cur = conn.execute(
        "INSERT INTO monuments (slug, name, latitude, longitude, coordinates_source_id, "
        "era, architectural_style, location, city) VALUES (?, ?, 28.6, 77.2, 1, "
        "'Mughal', 'Mughal', 'Test location', 'Delhi')",
        (slug, name),
    )
    return cur.lastrowid


def _claim(conn, monument_id, key, claim_type, is_legend, source_ids):
    cur = conn.execute(
        "INSERT INTO claims (monument_id, claim_key, claim_type, text, is_legend) "
        "VALUES (?, ?, ?, ?, ?)",
        (monument_id, key, claim_type, f"Text of {key}", is_legend),
    )
    claim_id = cur.lastrowid
    for sid in source_ids:
        conn.execute(
            "INSERT INTO monument_sources (claim_id, monument_id, source_id, note) "
            "VALUES (?, ?, ?, 'paraphrase')",
            (claim_id, monument_id, sid),
        )
    return claim_id


@pytest.fixture
def client(tmp_path):
    conn = sqlite3.connect(tmp_path / "test.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))

    for i, publisher in enumerate(["Pub A", "Pub B", "Pub A"], start=1):
        conn.execute(
            "INSERT INTO sources (source_key, url, title, publisher, source_type) "
            "VALUES (?, ?, ?, ?, 'government')",
            (f"s{i}", f"https://example.com/{i}", f"Source {i}", publisher),
        )

    alpha = _monument(conn, "alpha", "Alpha Tomb")  # verified, has a legend too
    beta = _monument(conn, "beta", "Beta Fort")  # verified
    gamma = _monument(conn, "gamma", "Gamma Gate")  # claim from one publisher only
    _monument(conn, "delta", "Delta Hall")  # no claims
    epsilon = _monument(conn, "epsilon", "Epsilon Well")  # only a legend

    a1 = _claim(conn, alpha, "built", "built", 0, [1, 2])
    _claim(conn, alpha, "ghost-story", "tradition", 1, [1])
    _claim(conn, beta, "built", "built", 0, [1, 2])
    _claim(conn, gamma, "built", "built", 0, [1, 3])  # both sources are Pub A
    _claim(conn, epsilon, "ghost-story", "tradition", 1, [1])

    conn.execute(
        "INSERT INTO monument_relationships (from_monument_id, to_monument_id, "
        "relation_type, note, claim_id) VALUES (?, ?, 'same_patron', 'shared patron', ?)",
        (alpha, beta, a1),
    )
    conn.execute(
        "INSERT INTO monument_relationships (from_monument_id, to_monument_id, "
        "relation_type, note, claim_id) VALUES (?, ?, 'same_dynasty', 'same dynasty', ?)",
        (alpha, gamma, a1),
    )
    conn.commit()

    app.dependency_overrides[get_db] = lambda: conn
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()
    conn.close()


def _assert_not_found(r):
    assert r.status_code == 404
    err = r.json()["error"]
    assert err["code"] == "MONUMENT_NOT_FOUND"
    assert err["message"] and err["hint"]


def test_profile_found_with_sources(client):
    r = client.get("/api/monuments/alpha")
    assert r.status_code == 200
    body = r.json()
    assert body["slug"] == "alpha"
    built = next(c for c in body["claims"] if c["key"] == "built")
    assert len(built["sources"]) == 2
    assert {s["publisher"] for s in built["sources"]} == {"Pub A", "Pub B"}
    assert len(body["sources"]) == 2  # deduplicated across claims


def test_legend_is_flagged(client):
    claims = client.get("/api/monuments/alpha").json()["claims"]
    legend = next(c for c in claims if c["key"] == "ghost-story")
    assert legend["is_legend"] is True
    built = next(c for c in claims if c["key"] == "built")
    assert built["is_legend"] is False


def test_missing_monument_returns_404_envelope(client):
    _assert_not_found(client.get("/api/monuments/does-not-exist"))


def test_single_publisher_monument_is_unverified(client):
    _assert_not_found(client.get("/api/monuments/gamma"))


def test_monument_without_claims_is_unverified(client):
    _assert_not_found(client.get("/api/monuments/delta"))


def test_legend_only_monument_is_unverified(client):
    _assert_not_found(client.get("/api/monuments/epsilon"))


def test_related_lists_verified_edges_only(client):
    r = client.get("/api/monuments/alpha/related")
    assert r.status_code == 200
    body = r.json()
    assert body["monument"]["slug"] == "alpha"
    assert [i["monument"]["slug"] for i in body["related"]] == ["beta"]
    item = body["related"][0]
    assert item["relation_type"] == "same_patron"
    assert item["direction"] == "outgoing"
    assert len(item["sources"]) == 2


def test_related_shows_incoming_edges(client):
    items = client.get("/api/monuments/beta/related").json()["related"]
    assert [(i["monument"]["slug"], i["direction"]) for i in items] == [("alpha", "incoming")]


def test_related_for_unverified_or_missing_returns_404(client):
    _assert_not_found(client.get("/api/monuments/gamma/related"))
    _assert_not_found(client.get("/api/monuments/does-not-exist/related"))