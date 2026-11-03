"""Migration 001: add story_type and audio_key to stories, keyed by (monument, language, story_type).

Safe to run repeatedly (checks column existence first).
Run from repo root: python -m backend.app.db.migrate_001_stories_type_audio
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

try:
    from app.db.init_db import default_db_path
except ModuleNotFoundError:
    from backend.app.db.init_db import default_db_path


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == column for r in rows)


WANTED_UNIQUE = "UNIQUE (monument_id, language, story_type)"

STORIES_DDL = """
CREATE TABLE stories (
    id            INTEGER PRIMARY KEY,
    monument_id   INTEGER NOT NULL REFERENCES monuments (id) ON DELETE RESTRICT,
    language      TEXT    NOT NULL DEFAULT 'en' CHECK (length(trim(language)) > 0),
    story_type    TEXT    NOT NULL DEFAULT 'visitor' CHECK (story_type IN ('visitor', 'academic')),
    body          TEXT    NOT NULL CHECK (length(trim(body)) > 0),
    audio_key     TEXT,
    model_version TEXT    NOT NULL CHECK (length(trim(model_version)) > 0),
    generated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (monument_id, language, story_type)
)
"""


def _rebuild_if_key_is_stale(conn: sqlite3.Connection) -> None:
    # SQLite cannot alter a UNIQUE constraint, and store_story upserts on this exact key.
    sql = re.sub(r"\s+", " ", conn.execute("SELECT sql FROM sqlite_master WHERE name = 'stories'").fetchone()[0])
    if WANTED_UNIQUE in sql:
        print("stories unique key already (monument, language, story_type), skipping.")
        return
    conn.execute("ALTER TABLE stories RENAME TO stories_old")
    conn.execute(STORIES_DDL)
    conn.execute(
        "INSERT OR REPLACE INTO stories "
        "(monument_id, language, story_type, body, audio_key, model_version, generated_at) "
        "SELECT monument_id, language, story_type, body, audio_key, model_version, generated_at "
        "FROM stories_old ORDER BY generated_at"
    )
    conn.execute("DROP TABLE stories_old")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_stories_monument ON stories (monument_id)")
    print("Rebuilt stories with unique key (monument, language, story_type).")


def run(db_path: Path | None = None) -> None:
    path = db_path or default_db_path()
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        conn.execute("BEGIN")

        if not _column_exists(conn, "stories", "story_type"):
            conn.execute(
                "ALTER TABLE stories ADD COLUMN "
                "story_type TEXT NOT NULL DEFAULT 'visitor' "
                "CHECK (story_type IN ('visitor', 'academic'))"
            )
            print("Added column: story_type")
        else:
            print("Column story_type already exists, skipping.")

        if not _column_exists(conn, "stories", "audio_key"):
            conn.execute("ALTER TABLE stories ADD COLUMN audio_key TEXT")
            print("Added column: audio_key")
        else:
            print("Column audio_key already exists, skipping.")

        _rebuild_if_key_is_stale(conn)

        conn.execute("COMMIT")
        print("Migration 001 complete.")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run()