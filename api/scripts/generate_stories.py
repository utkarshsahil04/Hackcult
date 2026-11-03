"""Batch story pre-generation script for Raahein.

Generates 15 monuments × 2 languages × 2 story types = 60 stories.
Writes results to the SQLite DB. Never called at request time.

Usage (from api/ with venv active):
    python -m scripts.generate_stories
    python -m scripts.generate_stories --slugs taj-mahal agra-fort
    python -m scripts.generate_stories --dry-run
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Allow running from api/ directory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.services.gemini import GeminiService
from app.services.stories import STORY_MODEL, generate_story, store_story

# backend/ is a sibling of api/
BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))
from app.db.init_db import connect, default_db_path

LANGUAGES = ["en", "hi"]
STORY_TYPES = ["visitor", "academic"]

ALL_SLUGS = [
    "taj-mahal", "agra-fort", "fatehpur-sikri", "itmad-ud-daulah", "mehtab-bagh",
    "akbars-tomb", "qutb-minar", "humayuns-tomb", "red-fort", "jama-masjid",
    "india-gate", "lotus-temple", "purana-qila", "safdarjung-tomb", "jantar-mantar",
]


def run(slugs: list[str], dry_run: bool = False) -> None:
    settings = get_settings()
    gemini = GeminiService(api_key=settings.gemini_api_key)
    conn = connect(default_db_path())

    total = len(slugs) * len(LANGUAGES) * len(STORY_TYPES)
    done = 0
    failures: list[str] = []

    print(f"Generating {total} stories (dry_run={dry_run})...\n")

    for slug in slugs:
        for lang in LANGUAGES:
            for story_type in STORY_TYPES:
                label = f"{slug}/{lang}/{story_type}"
                try:
                    body, check = generate_story(conn, gemini, slug, lang, story_type)
                    if check.unchecked_sentences:
                        print(f"  [WARN] {label}: {len(check.unchecked_sentences)} unchecked sentence(s):")
                        for s in check.unchecked_sentences:
                            print(f"         - {s[:120]}")
                    if not dry_run:
                        conn.execute("BEGIN")
                        store_story(conn, slug, lang, story_type, body, STORY_MODEL)
                        conn.execute("COMMIT")
                    done += 1
                    print(f"  [OK] {label} ({len(body)} chars)")
                except (ValueError, RuntimeError, OSError) as exc:
                    conn.execute("ROLLBACK")
                    failures.append(label)
                    print(f"  [FAIL] {label}: {exc}")
                # Respect free-tier rate limits: ~2 req/s max
                time.sleep(0.6)

    print(f"\nDone: {done}/{total} succeeded, {len(failures)} failed.")
    if failures:
        print("Failed:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)

    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Pre-generate Raahein stories.")
    ap.add_argument("--slugs", nargs="+", default=ALL_SLUGS, help="monument slugs to generate")
    ap.add_argument("--dry-run", action="store_true", help="generate but do not write to DB")
    args = ap.parse_args()
    run(args.slugs, dry_run=args.dry_run)