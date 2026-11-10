"""Every fact and connection note has a Hindi text, and none was left as copied English."""

import json
import re
from pathlib import Path

SEED = Path(__file__).resolve().parents[1] / "app/db/seed_data"


def _load(name: str):
    return json.loads((SEED / name).read_text(encoding="utf-8"))


def test_every_claim_and_connection_has_a_hindi_text():
    claims = {f"{c['monument']}/{c['key']}" for c in _load("claims.json")}
    links = {f"{e['from']}|{e['to']}|{e['type']}" for e in _load("relationships.json")}
    assert set(_load("claims_hi.json")) == claims
    assert set(_load("connections_hi.json")) == links


def test_translations_are_hindi_not_copied_english():
    for name in ("claims_hi.json", "connections_hi.json"):
        for key, text in _load(name).items():
            letters = re.findall(r"[A-Za-zऀ-ॿ]", text)
            hindi = sum("ऀ" <= ch <= "ॿ" for ch in letters)
            assert hindi / len(letters) > 0.8, key
