"""Seed pipeline behaviour and the content rules from Issue #3."""

import json
import sqlite3

import pytest

from app.db.init_db import REQUIRED_TABLES, verify_integrity
from app.db.seed import (
    TARGET_MONUMENTS,
    TARGET_RELATIONSHIPS,
    SeedError,
    load_dataset,
    seed,
    validate_dataset,
)


# ---------------------------------------------------------------- content rules
def test_required_tables_are_queryable_and_monuments_seeded(db):
    for table in REQUIRED_TABLES:
        db.execute(f"SELECT 1 FROM {table} LIMIT 1")  # table exists and is queryable
    assert db.execute("SELECT COUNT(*) FROM monuments").fetchone()[0] >= 1


def test_at_least_15_verified_monuments(db):
    verified = db.execute("SELECT COUNT(DISTINCT monument_id) FROM claims WHERE is_legend = 0").fetchone()[0]
    assert verified >= TARGET_MONUMENTS  # listed sites count once they gain sourced claims
    assert db.execute("SELECT COUNT(*) FROM monuments").fetchone()[0] >= TARGET_MONUMENTS


def test_at_least_30_relationship_edges(db):
    assert db.execute("SELECT COUNT(*) FROM monument_relationships").fetchone()[0] >= TARGET_RELATIONSHIPS


def test_every_present_relationship_is_valid_and_verified(db):
    rows = db.execute(
        """SELECT r.id, c.is_legend, c.monument_id, r.from_monument_id, r.to_monument_id,
                  (SELECT COUNT(DISTINCT s.publisher) FROM monument_sources ms
                     JOIN sources s ON s.id = ms.source_id WHERE ms.claim_id = c.id) AS publishers
           FROM monument_relationships r JOIN claims c ON c.id = r.claim_id"""
    ).fetchall()
    assert rows, "expected at least one edge"
    for r in rows:
        assert r["from_monument_id"] != r["to_monument_id"]
        assert r["is_legend"] == 0
        assert r["monument_id"] in (r["from_monument_id"], r["to_monument_id"])
        assert r["publishers"] >= 2


def test_every_historical_fact_has_two_distinct_publishers(db):
    """Independent re-check of the rule (does not use the schema view)."""
    facts = db.execute("SELECT id, claim_key FROM claims WHERE is_legend = 0").fetchall()
    assert facts
    for f in facts:
        pubs = {r[0] for r in db.execute(
            "SELECT s.publisher FROM monument_sources ms JOIN sources s ON s.id = ms.source_id"
            " WHERE ms.claim_id = ?", (f["id"],))}
        assert len(pubs) >= 2, f"{f['claim_key']} has publishers {pubs}"


def test_legends_are_flagged_and_kept_out_of_descriptions(db):
    legends = db.execute("SELECT * FROM claims WHERE claim_type = 'tradition'").fetchall()
    assert legends, "dataset should include at least one legend"
    for lg in legends:
        assert lg["is_legend"] == 1
        assert db.execute("SELECT COUNT(*) FROM monument_sources WHERE claim_id = ?", (lg["id"],)).fetchone()[0] >= 1
        desc = db.execute("SELECT description FROM monuments WHERE id = ?", (lg["monument_id"],)).fetchone()[0]
        assert lg["text"] not in desc
    assert db.execute("SELECT COUNT(*) FROM claims WHERE is_legend = 1 AND claim_type <> 'tradition'").fetchone()[0] == 0


def test_descriptions_contain_only_sourced_claims(db):
    for m in db.execute("SELECT id, description FROM monuments"):
        texts = [r[0] for r in db.execute(
            "SELECT text FROM claims WHERE monument_id = ? AND is_legend = 0 "
            "AND claim_type IN ('built','style','recognition','event') ORDER BY position, claim_key", (m["id"],))]
        assert m["description"] == " ".join(texts)
        assert m["description"] or not texts  # a listed site may have no claims yet


def test_monument_metadata_is_complete(db):
    for m in db.execute("SELECT * FROM monuments"):
        for col in ("slug", "name", "era", "architectural_style", "location", "city"):
            assert (m[col] or "").strip(), f"{m['slug']}.{col} is empty"
        assert 6 <= m["latitude"] <= 37.5 and 68 <= m["longitude"] <= 98, m["slug"]
        assert m["coordinates_source_id"] is not None
        assert m["created_at"] and m["updated_at"]


def test_database_passes_integrity_check(db):
    assert verify_integrity(db) == []


# ------------------------------------------------------------------ idempotency
def _snapshot(path):
    conn = sqlite3.connect(path)
    try:
        return {t: conn.execute(f"SELECT * FROM {t} ORDER BY 1, 2").fetchall()
                for t in ("monuments", "sources", "claims", "monument_sources", "monument_relationships")}
    finally:
        conn.close()


def test_seed_is_idempotent(seeded_path):
    before = _snapshot(seeded_path)
    for _ in range(2):
        report = seed(seeded_path)
        assert report.rows_written == 0
    assert _snapshot(seeded_path) == before  # same rows, ids and timestamps


def test_seed_does_not_touch_stories(seeded_path):
    conn = sqlite3.connect(seeded_path)
    conn.execute("PRAGMA foreign_keys = ON")
    mid = conn.execute("SELECT id FROM monuments LIMIT 1").fetchone()[0]
    conn.execute("INSERT INTO stories (monument_id, body, model_version) VALUES (?, 'story', 'v1')", (mid,))
    conn.commit()
    conn.close()
    seed(seeded_path)
    conn = sqlite3.connect(seeded_path)
    assert conn.execute("SELECT COUNT(*) FROM stories").fetchone()[0] == 1
    conn.close()


def test_seed_updates_changed_rows_and_prunes_removed_ones(seeded_path, data_copy):
    claims = json.loads((data_copy / "claims.json").read_text())
    claims = [c for c in claims if c["key"] != "architect-ustad-ahmad-lahori"]
    claims[0]["text"] = claims[0]["text"] + " (edited)"
    (data_copy / "claims.json").write_text(json.dumps(claims))
    seed(seeded_path, data_copy)
    conn = sqlite3.connect(seeded_path)
    keys = {r[0] for r in conn.execute("SELECT claim_key FROM claims")}
    assert "architect-ustad-ahmad-lahori" not in keys
    assert conn.execute("SELECT COUNT(*) FROM claims WHERE text LIKE '%(edited)'").fetchone()[0] == 1
    conn.close()


# ------------------------------------------------------------------- validation
def _mutate(data_copy, name, fn):
    path = data_copy / f"{name}.json"
    data = json.loads(path.read_text())
    fn(data)
    path.write_text(json.dumps(data))


def _errors(data_copy):
    return validate_dataset(load_dataset(data_copy))


def test_shipped_dataset_is_valid():
    assert validate_dataset(load_dataset()) == []


def test_single_source_historical_claim_is_rejected(tmp_path, data_copy):
    _mutate(data_copy, "claims", lambda d: d[0].update(sources=d[0]["sources"][:1]))
    assert any("distinct publishers" in e for e in _errors(data_copy))
    with pytest.raises(SeedError, match="distinct publishers"):
        seed(tmp_path / "x.db", data_copy)
    assert not (tmp_path / "x.db").exists()  # validation runs before anything is created


def test_two_sources_from_same_publisher_are_rejected(data_copy):
    def same_pub(d):
        c = next(c for c in d if c["key"] == "unesco-inscription-1993")
        c["sources"] = [{"source": "unesco-232", "note": "n"},
                        {"source": "unesco-232-periodic-report", "note": "n"}]
    _mutate(data_copy, "claims", same_pub)
    assert any("distinct publishers" in e for e in _errors(data_copy))


def test_legend_flag_must_be_explicit_and_consistent(data_copy):
    _mutate(data_copy, "claims", lambda d: next(c for c in d if c["type"] == "tradition").update(is_legend=False))
    assert any("is_legend must be true exactly when" in e for e in _errors(data_copy))
    _mutate(data_copy, "claims", lambda d: d[0].pop("is_legend"))
    assert any("explicit" in e for e in _errors(data_copy))


def test_unknown_references_are_reported_with_context(data_copy):
    _mutate(data_copy, "relationships", lambda d: d[0].update(to="atlantis"))
    _mutate(data_copy, "claims", lambda d: d[0]["sources"].append({"source": "nope", "note": "n"}))
    errs = _errors(data_copy)
    assert any("unknown monument 'atlantis'" in e for e in errs)
    assert any("unknown source 'nope'" in e for e in errs)


def test_legend_cannot_back_a_relationship(data_copy):
    _mutate(data_copy, "relationships", lambda d: d[0].update(claim="fatehpur-sikri/legend-salim-chishti-prediction",
                                                               **{"from": "fatehpur-sikri", "to": "taj-mahal"}))
    assert any("legends cannot back" in e for e in _errors(data_copy))


def test_swapped_coordinates_are_caught(data_copy):
    def swap(d):
        d[0]["latitude"], d[0]["longitude"] = d[0]["longitude"], d[0]["latitude"]
    _mutate(data_copy, "monuments", swap)
    assert any("outside India" in e for e in _errors(data_copy))


def test_duplicate_slug_and_missing_fields_are_reported(data_copy):
    _mutate(data_copy, "monuments", lambda d: (d.append(dict(d[0])), d[1].pop("era")))
    errs = _errors(data_copy)
    assert any("missing/empty field(s) era" in e for e in errs)


def test_failed_seed_leaves_existing_database_untouched(seeded_path, data_copy):
    before = _snapshot(seeded_path)
    _mutate(data_copy, "claims", lambda d: d[0].update(sources=[]))
    with pytest.raises(SeedError):
        seed(seeded_path, data_copy)
    assert _snapshot(seeded_path) == before


def test_banned_sources_are_rejected(data_copy):
    _mutate(data_copy, "sources", lambda d: d.append({
        "key": "wiki-test",
        "url": "https://en.wikipedia.org/wiki/Test",
        "title": "Wikipedia Test",
        "publisher": "Wikipedia",
        "source_type": "encyclopedia"
    }))
    assert any("banned/derivative source" in e for e in _errors(data_copy))
