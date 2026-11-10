"""Export the monuments table to frontend/lib/catalog.json (and their connections to connections.json), the only monument data the UI bundles.

Re-run after `python -m app.db.seed`: python tools/export_catalog.py
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "backend" / "data" / "raahein.db"
HI = json.loads((ROOT / "backend/app/db/seed_data/names_hi.json").read_text(encoding="utf-8"))
SEED = ROOT / "backend/app/db/seed_data"
# Hindi for every fact and connection note; names and source titles stay as published.
HI_CLAIMS = json.loads((SEED / "claims_hi.json").read_text(encoding="utf-8"))
HI_LINKS = json.loads((SEED / "connections_hi.json").read_text(encoding="utf-8"))
OUT = ROOT / "frontend" / "lib" / "catalog.json"
LINKS_OUT = OUT.with_name("connections.json")
HEADINGS = {
    "built": ("Origin", "उत्पत्ति"),
    "style": ("Architecture", "वास्तुकला"),
    "recognition": ("Recognition", "मान्यता"),
    "event": ("History", "इतिहास"),
    "relationship": ("Connections", "संबंध"),
    "tradition": ("Legend", "किंवदंती"),
}


def first_sentences(text: str, n: int = 2) -> str:
    return " ".join(re.split(r"(?<=[।.!?])\s+", text.strip())[:n])


def bi(text: str) -> dict[str, str]:
    return {"en": text, "hi": text}  # claims and sources are stored in English only


def main() -> None:
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    out = []
    for m in c.execute("SELECT * FROM monuments ORDER BY id").fetchall():
        claims = c.execute(
            "SELECT id, claim_key, claim_type, text, is_legend FROM claims WHERE monument_id = ? ORDER BY position, claim_key",
            (m["id"],),
        ).fetchall()
        sources: list[dict] = []
        index: dict[str, int] = {}
        sections = []
        for claim in claims:
            cited: list[int] = []
            for s in c.execute(
                "SELECT s.url, s.title, s.publisher FROM monument_sources ms JOIN sources s ON s.id = ms.source_id "
                "WHERE ms.claim_id = ? ORDER BY s.publisher",
                (claim["id"],),
            ).fetchall():
                if s["url"] not in index:
                    sources.append({"title": bi(s["title"]), "publisher": bi(s["publisher"]), "url": s["url"]})
                    index[s["url"]] = len(sources)
                cited.append(index[s["url"]])
            en, hi = HEADINGS[claim["claim_type"]]
            sections.append({
                "heading": {"en": en, "hi": hi},
                "text": {"en": claim["text"], "hi": HI_CLAIMS.get(f'{m["slug"]}/{claim["claim_key"]}', claim["text"])},
                "isLegend": bool(claim["is_legend"]),
                "source": cited[0] if cited else None,
                "cited": cited,  # every source behind the claim, so both publishers show
            })
        related = [r[0] for r in c.execute(
            "SELECT DISTINCT o.slug FROM monument_relationships r JOIN monuments o "
            "ON o.id = CASE WHEN r.from_monument_id = :m THEN r.to_monument_id ELSE r.from_monument_id END "
            "WHERE r.from_monument_id = :m OR r.to_monument_id = :m ORDER BY o.id",
            {"m": m["id"]},
        )]
        summary = {}
        for lang in ("en", "hi"):
            row = c.execute(
                "SELECT body FROM stories WHERE monument_id = ? AND language = ? AND story_type = 'visitor'",
                (m["id"], lang),
            ).fetchone()
            summary[lang] = first_sentences(row[0]) if row else ""
        out.append({
            "id": m["slug"],
            "name": {"en": m["name"], "hi": HI[m["slug"]]},
            "city": m["city"],
            "era": m["era"],
            "style": m["architectural_style"],
            "location": m["location"],
            "verified": any(not x["is_legend"] for x in claims),
            "summary": summary,
            "sections": sections,
            "sources": sources,
            "related": related,
            "lat": m["latitude"],
            "lng": m["longitude"],
        })
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(out)} monuments ({sum(x['verified'] for x in out)} verified) to {OUT}")

    # Every connection rests on a claim with two independent publishers, so the graph page can name them.
    links = [
        {
            "from": r["a"], "to": r["b"], "type": r["relation_type"], "note": r["note"],
            "note_hi": HI_LINKS.get(f'{r["a"]}|{r["b"]}|{r["relation_type"]}', r["note"]),
            "publishers": [p[0] for p in c.execute(
                "SELECT DISTINCT s.publisher FROM monument_sources ms JOIN sources s ON s.id = ms.source_id "
                "WHERE ms.claim_id = ? ORDER BY s.publisher", (r["claim_id"],))],
        }
        for r in c.execute(
            "SELECT a.slug AS a, b.slug AS b, r.relation_type, r.note, r.claim_id FROM monument_relationships r "
            "JOIN monuments a ON a.id = r.from_monument_id JOIN monuments b ON b.id = r.to_monument_id "
            "ORDER BY a.slug, b.slug, r.relation_type"
        )
    ]
    LINKS_OUT.write_text(json.dumps(links, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(links)} connections to {LINKS_OUT}")


if __name__ == "__main__":
    main()
