"""Migration 001: add story_type and audio_key to stories table and update UNIQUE constraint.

Safe to run repeatedly (checks column and constraint state first).
Run from repo root: python -m backend.app.db.migrate_001_stories_type_audio
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

try:
    from app.db.init_db import default_db_path
except ModuleNotFoundError:
    from backend.app.db.init_db import default_db_path


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == column for r in rows)


def run(db_path: Path | None = None) -> None:
    path = db_path or default_db_path()
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")

    try:
        conn.execute("BEGIN")

        sql_row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='stories'"
        ).fetchone()

        if sql_row and "UNIQUE (monument_id, language, story_type)" not in sql_row["sql"]:
            # Need to rebuild table with new schema matching schema.sql
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stories_new (
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
            )
            has_story_type = _column_exists(conn, "stories", "story_type")
            has_audio_key = _column_exists(conn, "stories", "audio_key")
            st_col = "story_type" if has_story_type else "'visitor'"
            ak_col = "audio_key" if has_audio_key else "NULL"

            conn.execute(
                f"""
                INSERT OR IGNORE INTO stories_new (id, monument_id, language, story_type, body, audio_key, model_version, generated_at)
                SELECT id, monument_id, language, {st_col}, body, {ak_col}, model_version, generated_at FROM stories
                """
            )
            conn.execute("DROP TABLE stories")
            conn.execute("ALTER TABLE stories_new RENAME TO stories")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_stories_monument ON stories (monument_id)")
            print("Migrated stories table to new schema with UNIQUE (monument_id, language, story_type)")
        else:
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

            conn.execute("CREATE INDEX IF NOT EXISTS ix_stories_monument ON stories (monument_id)")

        conn.execute("COMMIT")
        print("Migration 001 complete.")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()


if __name__ == "__main__":
    run()
