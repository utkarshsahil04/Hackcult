import os

os.environ.setdefault("GEMINI_API_KEY", "test-key")

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.services.stories import check_claims

SCHEMA = Path(__file__).resolve().parents[2] / "backend" / "app" / "db" / "schema.sql"


def _setup_db(tmp_path):
    conn = sqlite3.connect(tmp_path / "test.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))

    # Two distinct publishers required for a historical claim
    for i, (publisher, url) in enumerate(
        [("Pub A", "https://a.example.com"), ("Pub B", "https://b.example.com")], start=1
    ):
        conn.execute(
            "INSERT INTO sources (id, source_key, url, title, publisher, source_type) "
            "VALUES (?, ?, ?, 'Title', ?, 'government')",
            (i, f"src-{i}", url, publisher),
        )

    mid = conn.execute(
        "INSERT INTO monuments (slug, name, latitude, longitude, coordinates_source_id, "
        "era, architectural_style, location, city) VALUES (?, ?, 28.6, 77.2, 1, "
        "'Mughal', 'Mughal', 'Test location', 'Delhi')",
        ("taj-mahal", "Taj Mahal"),
    ).lastrowid

    cid = conn.execute(
        "INSERT INTO claims (monument_id, claim_key, claim_type, text, is_legend) "
        "VALUES (?, 'built', 'built', 'Built by Shah Jahan in 1632.', 0)",
        (mid,),
    ).lastrowid
    for sid in (1, 2):
        conn.execute(
            "INSERT INTO monument_sources (claim_id, monument_id, source_id, note) "
            "VALUES (?, ?, ?, 'Source note text')",
            (cid, mid, sid),
        )

    conn.commit()
    return conn, mid


@pytest.fixture
def client(tmp_path):
    conn, mid = _setup_db(tmp_path)

    app.dependency_overrides[get_db] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()
    conn.close()


@pytest.fixture
def client_with_story(tmp_path):
    conn, mid = _setup_db(tmp_path)

    conn.execute(
        "INSERT INTO stories (monument_id, language, story_type, body, model_version) "
        "VALUES (?, 'en', 'visitor', 'As you stand here, the Taj Mahal rises before you.', 'gemini-2.0-flash-lite')",
        (mid,),
    )
    conn.commit()

    app.dependency_overrides[get_db] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()
    conn.close()


# --- GET /api/stories/{slug} ---

def test_story_not_found(client):
    r = client.get("/api/stories/taj-mahal")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "STORY_NOT_FOUND"


def test_story_not_found_unknown_slug(client):
    r = client.get("/api/stories/does-not-exist")
    assert r.status_code == 404


def test_story_returns_stored(client_with_story):
    r = client_with_story.get("/api/stories/taj-mahal?language=en&story_type=visitor")
    assert r.status_code == 200
    data = r.json()
    assert data["slug"] == "taj-mahal"
    assert data["language"] == "en"
    assert data["story_type"] == "visitor"
    assert "Taj Mahal" in data["body"]
    assert data["model_version"] == "gemini-2.0-flash-lite"


def test_story_defaults_en_visitor(client_with_story):
    r = client_with_story.get("/api/stories/taj-mahal")
    assert r.status_code == 200
    assert r.json()["language"] == "en"
    assert r.json()["story_type"] == "visitor"


def test_story_wrong_language_rejected(client_with_story):
    r = client_with_story.get("/api/stories/taj-mahal?language=fr")
    assert r.status_code in (400, 422)


def test_story_wrong_type_rejected(client_with_story):
    r = client_with_story.get("/api/stories/taj-mahal?story_type=kids")
    assert r.status_code in (400, 422)


def test_story_missing_type_returns_404(client_with_story):
    # 'academic' not yet generated — should 404 cleanly
    r = client_with_story.get("/api/stories/taj-mahal?story_type=academic")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "STORY_NOT_FOUND"

# --- Claim checking tests ---

def test_check_claims_passes_grounded_story():
    claims = [
        {
            "text": "Commissioned by Mughal Emperor Shah Jahan in 1632.",
            "source_notes": ["White marble mausoleum housing the tomb of Mumtaz Mahal."],
        }
    ]
    story = (
        "As you stand before the monument, the white marble mausoleum rises gracefully. "
        "It was commissioned by Mughal Emperor Shah Jahan in 1632. "
        "Welcome to this wonder."
    )
    res = check_claims(story, claims)
    assert res.passed is True
    assert res.unchecked_sentences == []


def test_check_claims_fails_hallucinated_sentence():
    claims = [
        {
            "text": "Commissioned by Mughal Emperor Shah Jahan in 1632.",
            "source_notes": ["White marble mausoleum housing the tomb of Mumtaz Mahal."],
        }
    ]
    story = (
        "It was commissioned by Mughal Emperor Shah Jahan in 1632. "
        "The Apollo 11 spacecraft landed humans on the lunar surface in July."
    )
    res = check_claims(story, claims)
    assert res.passed is False
    assert len(res.unchecked_sentences) == 1
    assert "Apollo 11" in res.unchecked_sentences[0]


def test_check_claims_short_sentences_skipped():
    claims = [{"text": "Historic fortress built in Agra.", "source_notes": []}]
    story = "Look up. Welcome. It is grand."
    res = check_claims(story, claims)
    assert res.passed is True
    assert res.unchecked_sentences == []
