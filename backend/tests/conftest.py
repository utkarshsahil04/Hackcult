import shutil
from pathlib import Path

import pytest

from app.db.init_db import connect, init_db
from app.db.seed import DATA_DIR, seed


@pytest.fixture()
def empty_db(tmp_path: Path):
    """A schema-only database (no seed data)."""
    path = init_db(tmp_path / "empty.db")
    conn = connect(path)
    yield conn
    conn.close()


@pytest.fixture()
def seeded_path(tmp_path: Path) -> Path:
    path = tmp_path / "seeded.db"
    seed(path)
    return path


@pytest.fixture()
def db(seeded_path: Path):
    conn = connect(seeded_path)
    yield conn
    conn.close()


@pytest.fixture()
def data_copy(tmp_path: Path) -> Path:
    """A throw-away copy of the seed JSON files that tests may mutate."""
    dest = tmp_path / "seed_data"
    shutil.copytree(DATA_DIR, dest, ignore=shutil.ignore_patterns("README.md"))
    return dest
