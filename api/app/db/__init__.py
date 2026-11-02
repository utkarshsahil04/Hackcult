from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

from app.config import get_settings
from app.errors import AppError

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "backend"
DEFAULT_DB_PATH = BACKEND_ROOT / "data" / "raahein.db"

# Allow app.db package to discover backend database modules (such as app.db.init_db)
_backend_db = BACKEND_ROOT / "app" / "db"
if _backend_db.is_dir() and str(_backend_db) not in __path__:
    __path__.append(str(_backend_db))


def resolve_db_path() -> Path:
    raw = get_settings().sqlite_db_path
    if not raw:
        return DEFAULT_DB_PATH
    path = Path(raw)
    return path if path.is_absolute() else BACKEND_ROOT / path


def get_db() -> Iterator[sqlite3.Connection]:
    path = resolve_db_path()
    if not path.is_file():
        raise AppError(
            503,
            "DATABASE_UNAVAILABLE",
            "The monument database is not available.",
            "Build it with `python -m app.db.seed` from the backend folder.",
        )
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()
