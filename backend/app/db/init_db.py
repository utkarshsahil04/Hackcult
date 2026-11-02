"""Database initialisation: connection helpers and schema creation.

This module deliberately contains **no data**.  Seed content lives in
``seed_data/`` and is loaded by :mod:`app.db.seed`.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1
SCHEMA_PATH = Path(__file__).with_name("schema.sql")
BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BACKEND_ROOT / "data" / "raahein.db"

REQUIRED_TABLES = (
    "monuments",
    "sources",
    "monument_sources",
    "monument_relationships",
    "stories",
)


def default_db_path() -> Path:
    """``SQLITE_DB_PATH`` if set (relative paths resolve from ``backend/``), else the default."""
    raw = os.environ.get("SQLITE_DB_PATH")
    if not raw:
        return DEFAULT_DB_PATH
    path = Path(raw)
    return path if path.is_absolute() else BACKEND_ROOT / path


def connect(db_path: str | Path | None = None, *, read_only: bool = False) -> sqlite3.Connection:
    """Open a connection with foreign keys enforced and ``sqlite3.Row`` rows.

    ``isolation_level=None`` leaves transaction control to the caller.
    """
    path = Path(db_path) if db_path is not None else default_db_path()
    if read_only:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, isolation_level=None)
    else:
        conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str | Path | None = None) -> Path:
    """Create the database file and apply the schema.  Safe to call repeatedly."""
    path = Path(db_path) if db_path is not None else default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(path)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    finally:
        conn.close()
    return path


def verify_integrity(conn: sqlite3.Connection) -> list[str]:
    """Return human-readable rule violations (empty list means the database is sound)."""
    problems: list[str] = []
    for row in conn.execute("PRAGMA foreign_key_check"):
        problems.append(f"foreign key violation in table {row[0]!r} (rowid {row[1]})")
    for row in conn.execute(
        "SELECT m.slug, v.claim_key, v.is_legend, v.source_count, v.publisher_count "
        "FROM v_claim_rule_violations v JOIN monuments m ON m.id = v.monument_id"
    ):
        need = "at least 1 source" if row["is_legend"] else "at least 2 distinct publishers"
        problems.append(
            f"claim {row['slug']}/{row['claim_key']} needs {need} "
            f"(has {row['source_count']} sources, {row['publisher_count']} publishers)"
        )
    return problems


if __name__ == "__main__":  # python -m app.db.init_db
    print(f"Initialised {init_db()}")
