"""Idempotent seed pipeline for the Raahein heritage database.

Usage (from ``backend/``)::

    python -m app.db.seed                 # create/refresh the DB from seed_data/
    python -m app.db.seed --check         # validate the data files only
    python -m app.db.seed --strict        # also fail while Issue #3 targets are unmet

Data lives in ``seed_data/*.json``; schema lives in ``schema.sql``.  Running the
seed repeatedly leaves the database unchanged (no duplicates, no timestamp churn).
The seed *owns* the rows it manages: rows removed from the data files are pruned.
``stories`` is never touched.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.db.init_db import connect, init_db, verify_integrity

DATA_DIR = Path(__file__).with_name("seed_data")

# Issue #3 acceptance targets (reported by --strict and by the tests).
TARGET_MONUMENTS = 15
TARGET_RELATIONSHIPS = 30

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# Sanity box around India: catches swapped or mistyped coordinates.
LAT_RANGE, LON_RANGE = (6.0, 37.5), (68.0, 98.0)
SOURCE_TYPES = {"intergovernmental", "government", "encyclopedia", "news", "academic", "other"}
CLAIM_TYPES = {"built", "style", "recognition", "event", "relationship", "tradition"}
RELATION_TYPES = {
    "architectural_influence", "architectural_precursor", "same_patron", "same_dynasty", "successor_of",
    "capital_relationship", "burial_association", "historical_event",
    "co_located_world_heritage",
}
# Claim types that make up a monument's generated description.
DESCRIPTION_TYPES = {"built", "style", "recognition", "event"}
BANNED_SOURCES = ("wikipedia", "wikiwand", "newworldencyclopedia", "wikimedia", "indiatv")


class SeedError(Exception):
    """Raised when seed data is invalid. ``errors`` lists every problem found."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("Seed data invalid:\n  - " + "\n  - ".join(errors))


@dataclass
class SeedReport:
    db_path: Path
    rows_written: int = 0
    counts: dict[str, int] = field(default_factory=dict)
    shortfalls: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- loading
def load_dataset(data_dir: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    base = Path(data_dir) if data_dir else DATA_DIR
    dataset: dict[str, list[dict[str, Any]]] = {}
    for name in ("sources", "monuments", "claims", "relationships"):
        path = base / f"{name}.json"
        try:
            dataset[name] = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise SeedError([f"missing data file: {path}"]) from None
        except json.JSONDecodeError as exc:
            raise SeedError([f"{path.name}: invalid JSON ({exc})"]) from None
        if not isinstance(dataset[name], list):
            raise SeedError([f"{path.name}: top level must be a list"])
    _merge_listed_sites(base, dataset)
    return dataset


def _merge_listed_sites(base: Path, dataset: dict[str, list[dict[str, Any]]]) -> None:
    """Add real OSM-located sites (sites.json) as listed monuments: plannable, but with no
    claims, so the API shows them as "story pending" instead of inventing history."""
    path = base / "sites.json"
    if not path.is_file():
        return
    for site in json.loads(path.read_text(encoding="utf-8")):
        key = f"osm-{site['osm_type']}-{site['osm_id']}"
        dataset["sources"].append({
            "key": key, "url": f"https://www.openstreetmap.org/{site['osm_type']}/{site['osm_id']}",
            "title": f"{site['name']} (OpenStreetMap)", "publisher": "OpenStreetMap contributors",
            "source_type": "other",
        })
        listed = {k: v for k, v in site.items() if k not in ("osm_type", "osm_id")}
        dataset["monuments"].append({**listed, "coordinates_source": key, "listed": True})


# ------------------------------------------------------------------------ validation
def _need(rec: dict, keys: tuple[str, ...], where: str, errors: list[str]) -> bool:
    missing = [k for k in keys if rec.get(k) in (None, "")]
    if missing:
        errors.append(f"{where}: missing/empty field(s) {', '.join(missing)}")
    return not missing


def validate_dataset(ds: dict[str, list[dict[str, Any]]]) -> list[str]:
    """Check everything the database cannot, and everything it can, before writing."""
    errors: list[str] = []

    sources: dict[str, dict] = {}
    urls: set[str] = set()
    for i, s in enumerate(ds["sources"]):
        where = f"sources[{i}] ({s.get('key', '?')})"
        if not _need(s, ("key", "url", "title", "publisher", "source_type"), where, errors):
            continue
        url_lower, pub_lower = s["url"].lower(), s["publisher"].lower()
        for banned in BANNED_SOURCES:
            if banned in url_lower or banned in pub_lower:
                errors.append(f"{where}: banned/derivative source {banned!r} is not allowed")
        if s["key"] in sources:
            errors.append(f"{where}: duplicate source key")
        if s["url"] in urls:
            errors.append(f"{where}: duplicate url {s['url']}")
        if not s["url"].startswith("https://"):
            errors.append(f"{where}: url must start with https://")
        if s["source_type"] not in SOURCE_TYPES:
            errors.append(f"{where}: unknown source_type {s['source_type']!r}")
        sources[s["key"]] = s
        urls.add(s["url"])

    monuments: dict[str, dict] = {}
    for i, m in enumerate(ds["monuments"]):
        where = f"monuments[{i}] ({m.get('slug', '?')})"
        if not _need(m, ("slug", "name", "latitude", "longitude", "coordinates_source",
                         "era", "architectural_style", "location", "city"), where, errors):
            continue
        if not SLUG_RE.match(m["slug"]):
            errors.append(f"{where}: slug must be lowercase letters, digits and hyphens")
        if m["slug"] in monuments:
            errors.append(f"{where}: duplicate slug")
        lat, lon = m["latitude"], m["longitude"]
        if not (isinstance(lat, (int, float)) and isinstance(lon, (int, float))):
            errors.append(f"{where}: latitude/longitude must be numbers")
        elif not (LAT_RANGE[0] <= lat <= LAT_RANGE[1] and LON_RANGE[0] <= lon <= LON_RANGE[1]):
            errors.append(f"{where}: coordinates ({lat}, {lon}) fall outside India - swapped lat/lon?")
        if m["coordinates_source"] not in sources:
            errors.append(f"{where}: unknown coordinates_source {m['coordinates_source']!r}")
        monuments[m["slug"]] = m

    claims: dict[str, dict] = {}  # "<slug>/<key>" -> claim
    for i, c in enumerate(ds["claims"]):
        where = f"claims[{i}] ({c.get('monument', '?')}/{c.get('key', '?')})"
        if not _need(c, ("monument", "key", "type", "text", "sources"), where, errors):
            continue
        if "is_legend" not in c or not isinstance(c["is_legend"], bool):
            errors.append(f"{where}: is_legend must be an explicit true/false")
            continue
        ref = f"{c['monument']}/{c['key']}"
        if ref in claims:
            errors.append(f"{where}: duplicate claim key")
        if c["monument"] not in monuments:
            errors.append(f"{where}: unknown monument {c['monument']!r}")
        if c["type"] not in CLAIM_TYPES:
            errors.append(f"{where}: unknown type {c['type']!r}")
        if c["is_legend"] != (c["type"] == "tradition"):
            errors.append(f"{where}: is_legend must be true exactly when type is 'tradition'")
        publishers: set[str] = set()
        seen: set[str] = set()
        for link in c["sources"]:
            skey = link.get("source")
            if skey not in sources:
                errors.append(f"{where}: unknown source {skey!r}")
                continue
            if skey in seen:
                errors.append(f"{where}: source {skey!r} listed twice")
            seen.add(skey)
            if not (link.get("note") or "").strip():
                errors.append(f"{where}: source {skey!r} needs a non-empty note")
            publishers.add(sources[skey]["publisher"])
        if c["is_legend"]:
            if not seen:
                errors.append(f"{where}: legend needs at least 1 source")
        elif len(publishers) < 2:
            errors.append(
                f"{where}: historical claim needs >= 2 sources from distinct publishers "
                f"(has {len(seen)} source(s), {len(publishers)} publisher(s))"
            )
        claims[ref] = c

    for slug in monuments:
        if monuments[slug].get("listed"):
            continue
        if not any(c["monument"] == slug and not c["is_legend"] and c["type"] in DESCRIPTION_TYPES
                   for c in claims.values()):
            errors.append(f"monument {slug!r}: needs at least one sourced historical claim for its description")

    seen_edges: set[tuple[str, str, str]] = set()
    for i, r in enumerate(ds["relationships"]):
        where = f"relationships[{i}] ({r.get('from', '?')} -> {r.get('to', '?')})"
        if not _need(r, ("from", "to", "type", "claim", "note"), where, errors):
            continue
        for end in ("from", "to"):
            if r[end] not in monuments:
                errors.append(f"{where}: unknown monument {r[end]!r} in '{end}'")
        if r["from"] == r["to"]:
            errors.append(f"{where}: a monument cannot relate to itself")
        if r["type"] not in RELATION_TYPES:
            errors.append(f"{where}: unknown relation type {r['type']!r}")
        edge = (r["from"], r["to"], r["type"])
        if edge in seen_edges:
            errors.append(f"{where}: duplicate edge")
        seen_edges.add(edge)
        claim = claims.get(r["claim"])
        if claim is None:
            errors.append(f"{where}: unknown claim {r['claim']!r} (expected '<monument>/<claim-key>')")
        else:
            if claim["is_legend"]:
                errors.append(f"{where}: legends cannot back a relationship")
            if claim["monument"] not in (r["from"], r["to"]):
                errors.append(f"{where}: claim must be about one of the two endpoints")
    return errors


def target_shortfalls(ds: dict[str, list[dict[str, Any]]]) -> list[str]:
    out = []
    verified = sum(1 for m in ds["monuments"] if not m.get("listed"))
    if verified != TARGET_MONUMENTS:
        out.append(f"verified monuments: {verified} of {TARGET_MONUMENTS}")
    if len(ds["relationships"]) < TARGET_RELATIONSHIPS:
        out.append(f"relationship edges: {len(ds['relationships'])} of {TARGET_RELATIONSHIPS}")
    return out


# ------------------------------------------------------------------------- seeding
def _description(slug: str, claims: dict[str, dict]) -> str:
    own = [c for c in claims.values()
           if c["monument"] == slug and not c["is_legend"] and c["type"] in DESCRIPTION_TYPES]
    return " ".join(c["text"] for c in sorted(own, key=lambda c: (c.get("position", 0), c["key"])))


def _apply(conn: sqlite3.Connection, ds: dict[str, list[dict[str, Any]]]) -> None:
    now = "strftime('%Y-%m-%dT%H:%M:%SZ','now')"
    claims = {f"{c['monument']}/{c['key']}": c for c in ds["claims"]}

    # sources -------------------------------------------------------------
    for s in ds["sources"]:
        conn.execute(
            """INSERT INTO sources (source_key, url, title, publisher, source_type)
               VALUES (:key, :url, :title, :publisher, :source_type)
               ON CONFLICT(source_key) DO UPDATE SET url=excluded.url, title=excluded.title,
                   publisher=excluded.publisher, source_type=excluded.source_type
               WHERE url IS NOT excluded.url OR title IS NOT excluded.title
                  OR publisher IS NOT excluded.publisher OR source_type IS NOT excluded.source_type""",
            s,
        )
    source_id = {r["source_key"]: r["id"] for r in conn.execute("SELECT id, source_key FROM sources")}

    # monuments -----------------------------------------------------------
    for m in ds["monuments"]:
        params = {**m, "description": _description(m["slug"], claims),
                  "coord_src": source_id[m["coordinates_source"]]}
        conn.execute(
            f"""INSERT INTO monuments (slug, name, description, latitude, longitude,
                    coordinates_source_id, era, architectural_style, location, city)
                VALUES (:slug, :name, :description, :latitude, :longitude, :coord_src,
                    :era, :architectural_style, :location, :city)
                ON CONFLICT(slug) DO UPDATE SET name=excluded.name, description=excluded.description,
                    latitude=excluded.latitude, longitude=excluded.longitude,
                    coordinates_source_id=excluded.coordinates_source_id, era=excluded.era,
                    architectural_style=excluded.architectural_style, location=excluded.location,
                    city=excluded.city, updated_at={now}
                WHERE name IS NOT excluded.name OR description IS NOT excluded.description
                   OR latitude IS NOT excluded.latitude OR longitude IS NOT excluded.longitude
                   OR coordinates_source_id IS NOT excluded.coordinates_source_id
                   OR era IS NOT excluded.era OR architectural_style IS NOT excluded.architectural_style
                   OR location IS NOT excluded.location OR city IS NOT excluded.city""",
            params,
        )
    monument_id = {r["slug"]: r["id"] for r in conn.execute("SELECT id, slug FROM monuments")}

    # claims --------------------------------------------------------------
    for c in ds["claims"]:
        params = {"mid": monument_id[c["monument"]], "key": c["key"], "type": c["type"],
                  "text": c["text"], "legend": int(c["is_legend"]), "pos": c.get("position", 0)}
        conn.execute(
            f"""INSERT INTO claims (monument_id, claim_key, claim_type, text, is_legend, position)
                VALUES (:mid, :key, :type, :text, :legend, :pos)
                ON CONFLICT(monument_id, claim_key) DO UPDATE SET claim_type=excluded.claim_type,
                    text=excluded.text, is_legend=excluded.is_legend, position=excluded.position,
                    updated_at={now}
                WHERE claim_type IS NOT excluded.claim_type OR text IS NOT excluded.text
                   OR is_legend IS NOT excluded.is_legend OR position IS NOT excluded.position""",
            params,
        )
    claim_id = {(r["slug"], r["claim_key"]): r["id"] for r in conn.execute(
        "SELECT c.id, c.claim_key, m.slug FROM claims c JOIN monuments m ON m.id = c.monument_id")}

    # evidence links ------------------------------------------------------
    wanted_links: set[tuple[int, int]] = set()
    for c in ds["claims"]:
        cid = claim_id[(c["monument"], c["key"])]
        for link in c["sources"]:
            sid = source_id[link["source"]]
            wanted_links.add((cid, sid))
            conn.execute(
                """INSERT INTO monument_sources (claim_id, monument_id, source_id, note)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(claim_id, source_id) DO UPDATE SET note=excluded.note
                   WHERE note IS NOT excluded.note""",
                (cid, monument_id[c["monument"]], sid, link["note"].strip()),
            )

    # relationships -------------------------------------------------------
    wanted_edges: set[tuple[int, int, str]] = set()
    for r in ds["relationships"]:
        cm, ck = r["claim"].split("/", 1)
        edge = (monument_id[r["from"]], monument_id[r["to"]], r["type"])
        wanted_edges.add(edge)
        conn.execute(
            """INSERT INTO monument_relationships
                   (from_monument_id, to_monument_id, relation_type, note, claim_id)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(from_monument_id, to_monument_id, relation_type)
               DO UPDATE SET note=excluded.note, claim_id=excluded.claim_id
               WHERE note IS NOT excluded.note OR claim_id IS NOT excluded.claim_id""",
            (*edge, r["note"], claim_id[(cm, ck)]),
        )

    # prune rows the data files no longer contain (children first) ---------
    for row in conn.execute(
            "SELECT id, from_monument_id f, to_monument_id t, relation_type r FROM monument_relationships").fetchall():
        if (row["f"], row["t"], row["r"]) not in wanted_edges:
            conn.execute("DELETE FROM monument_relationships WHERE id = ?", (row["id"],))
    for row in conn.execute("SELECT claim_id, source_id FROM monument_sources").fetchall():
        if (row["claim_id"], row["source_id"]) not in wanted_links:
            conn.execute("DELETE FROM monument_sources WHERE claim_id = ? AND source_id = ?",
                         (row["claim_id"], row["source_id"]))
    wanted_claims = {claim_id[(c["monument"], c["key"])] for c in ds["claims"]}
    for row in conn.execute("SELECT id FROM claims").fetchall():
        if row["id"] not in wanted_claims:
            conn.execute("DELETE FROM claims WHERE id = ?", (row["id"],))
    wanted_slugs = {m["slug"] for m in ds["monuments"]}
    for row in conn.execute("SELECT id, slug FROM monuments").fetchall():
        if row["slug"] not in wanted_slugs:  # stories use ON DELETE RESTRICT, so this fails loudly
            conn.execute("DELETE FROM monuments WHERE id = ?", (row["id"],))
    wanted_sources = {source_id[s["key"]] for s in ds["sources"]}
    for row in conn.execute("SELECT id FROM sources").fetchall():
        if row["id"] not in wanted_sources:
            conn.execute("DELETE FROM sources WHERE id = ?", (row["id"],))


def seed(db_path: str | Path | None = None, data_dir: Path | None = None) -> SeedReport:
    """Validate the data, then apply it in a single transaction."""
    ds = load_dataset(data_dir)
    errors = validate_dataset(ds)
    if errors:
        raise SeedError(errors)

    path = init_db(db_path)
    conn = connect(path)
    try:
        before = conn.total_changes
        conn.execute("BEGIN IMMEDIATE")
        try:
            _apply(conn, ds)
            problems = verify_integrity(conn)
            if problems:
                raise SeedError(problems)
            conn.execute("COMMIT")
        except sqlite3.IntegrityError as exc:
            conn.execute("ROLLBACK")
            raise SeedError([f"database rejected the data: {exc}"]) from exc
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("monuments", "sources", "claims", "monument_sources",
                            "monument_relationships", "stories")}
        return SeedReport(path, conn.total_changes - before, counts, target_shortfalls(ds))
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Seed the Raahein SQLite database.")
    ap.add_argument("--db", type=Path, help="database path (default: $SQLITE_DB_PATH or backend/data/raahein.db)")
    ap.add_argument("--data-dir", type=Path, help="directory with the seed JSON files")
    ap.add_argument("--check", action="store_true", help="validate the data files only")
    ap.add_argument("--strict", action="store_true", help="exit non-zero if Issue #3 targets are not met")
    args = ap.parse_args(argv)
    try:
        if args.check:
            ds = load_dataset(args.data_dir)
            errors = validate_dataset(ds)
            if errors:
                raise SeedError(errors)
            report = SeedReport(Path("-"), shortfalls=target_shortfalls(ds))
            print("Seed data is valid.")
        else:
            report = seed(args.db, args.data_dir)
            print(f"Seeded {report.db_path}  (rows written: {report.rows_written})")
            for table, n in report.counts.items():
                print(f"  {table:24s}{n}")
    except SeedError as exc:
        print(exc, file=sys.stderr)
        return 1
    for gap in report.shortfalls:
        print(f"WARNING: Issue #3 target not met - {gap}", file=sys.stderr)
    return 1 if (args.strict and report.shortfalls) else 0


if __name__ == "__main__":
    raise SystemExit(main())
