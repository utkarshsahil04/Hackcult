"""Migration 001: add story_type and audio_key to stories table.

Safe to run repeatedly (checks column existence first).
Run from repo root: python -m backend.app.db.migrate_001_stories_type_audio
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from app.db.init_db import default_db_path


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == column for r in rows)


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

        conn.execute("COMMIT")
        print("Migration 001 complete.")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run()