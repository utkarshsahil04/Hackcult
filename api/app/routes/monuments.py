import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends

from app.db import get_db
from app.errors import AppError
from app.schemas import (
    ClaimOut,
    MonumentProfile,
    MonumentSummary,
    RelatedItem,
    RelatedResponse,
    SourceOut,
)

router = APIRouter(prefix="/api/monuments")

Db = Annotated[sqlite3.Connection, Depends(get_db)]

# A monument is "verified" when it has at least one historical (non-legend) claim
# and none of its claims break the two-publisher rule.
_VERIFIED = """
EXISTS (SELECT 1 FROM claims c WHERE c.monument_id = {m}.id AND c.is_legend = 0)
AND NOT EXISTS (SELECT 1 FROM v_claim_rule_violations v WHERE v.monument_id = {m}.id)
"""


def _not_found() -> AppError:
    return AppError(
        404,
        "MONUMENT_NOT_FOUND",
        "No verified monument with that id.",
        "Use a monument slug such as 'taj-mahal' or 'humayuns-tomb'.",
    )


def _get_verified_monument(conn: sqlite3.Connection, slug: str) -> sqlite3.Row:
    row = conn.execute(
        f"SELECT * FROM monuments m WHERE m.slug = ? AND {_VERIFIED.format(m='m')}",
        (slug,),
    ).fetchone()
    if row is None:
        raise _not_found()
    return row


def _source_out(row: sqlite3.Row, *, with_note: bool) -> SourceOut:
    return SourceOut(
        title=row["title"],
        url=row["url"],
        publisher=row["publisher"],
        source_type=row["source_type"],
        note=row["note"] if with_note else None,
    )


@router.get("/{slug}", response_model=MonumentProfile)
def get_monument(slug: str, conn: Db):
    m = _get_verified_monument(conn, slug)

    claim_rows = conn.execute(
        "SELECT id, claim_key, claim_type, text, is_legend FROM claims "
        "WHERE monument_id = ? ORDER BY position, claim_key",
        (m["id"],),
    ).fetchall()
    source_rows = conn.execute(
        "SELECT ms.claim_id, ms.note, s.title, s.url, s.publisher, s.source_type "
        "FROM monument_sources ms JOIN sources s ON s.id = ms.source_id "
        "WHERE ms.monument_id = ? ORDER BY s.publisher, s.title",
        (m["id"],),
    ).fetchall()

    by_claim: dict[int, list[SourceOut]] = {}
    unique: dict[str, SourceOut] = {}
    for r in source_rows:
        by_claim.setdefault(r["claim_id"], []).append(_source_out(r, with_note=True))
        unique.setdefault(r["url"], _source_out(r, with_note=False))

    claims = [
        ClaimOut(
            key=c["claim_key"],
            type=c["claim_type"],
            text=c["text"],
            is_legend=bool(c["is_legend"]),
            sources=by_claim.get(c["id"], []),
        )
        for c in claim_rows
    ]
    return MonumentProfile(
        slug=m["slug"],
        name=m["name"],
        description=m["description"],
        latitude=m["latitude"],
        longitude=m["longitude"],
        era=m["era"],
        architectural_style=m["architectural_style"],
        location=m["location"],
        city=m["city"],
        claims=claims,
        sources=list(unique.values()),
    )


@router.get("/{slug}/related", response_model=RelatedResponse)
def get_related(slug: str, conn: Db):
    m = _get_verified_monument(conn, slug)

    edge_rows = conn.execute(
        f"""
        SELECT r.relation_type, r.note, r.claim_id,
               CASE WHEN r.from_monument_id = :mid THEN 'outgoing' ELSE 'incoming' END
                   AS direction,
               o.slug, o.name, o.city
        FROM monument_relationships r
        JOIN monuments o
          ON o.id = CASE WHEN r.from_monument_id = :mid
                         THEN r.to_monument_id ELSE r.from_monument_id END
        WHERE (r.from_monument_id = :mid OR r.to_monument_id = :mid)
          AND {_VERIFIED.format(m='o')}
        ORDER BY o.name, r.relation_type
        """,
        {"mid": m["id"]},
    ).fetchall()

    items: list[RelatedItem] = []
    for e in edge_rows:
        src_rows = conn.execute(
            "SELECT ms.note, s.title, s.url, s.publisher, s.source_type "
            "FROM monument_sources ms JOIN sources s ON s.id = ms.source_id "
            "WHERE ms.claim_id = ? ORDER BY s.publisher",
            (e["claim_id"],),
        ).fetchall()
        items.append(
            RelatedItem(
                relation_type=e["relation_type"],
                direction=e["direction"],
                note=e["note"],
                monument=MonumentSummary(slug=e["slug"], name=e["name"], city=e["city"]),
                sources=[_source_out(r, with_note=True) for r in src_rows],
            )
        )

    return RelatedResponse(
        monument=MonumentSummary(slug=m["slug"], name=m["name"], city=m["city"]),
        related=items,
    )