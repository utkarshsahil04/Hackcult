"""Digitise archive scans into draft claims; a human reviewer approves them before visitors see them.

Archive data lives in its own writable SQLite file (raahein.db ships read-only in the deploy image).
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import logging
import re
import sqlite3
import time
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Form, Header, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel

from app.config import get_settings
from app.db import BACKEND_ROOT, get_db
from app.errors import AppError
from app.services.gemini import GeminiService

logger = logging.getLogger("raahein.api")
router = APIRouter(prefix="/api")

_MAX_BYTES = 6 * 1024 * 1024
_MIMES = {"image/jpeg", "image/png", "image/webp"}
_RIGHTS = ("own-photo", "public-domain", "cc-by", "cc-by-sa")
_LIMIT, _WINDOW = 20, 86_400
_rate_store: dict[str, dict] = defaultdict(lambda: {"count": 0, "start": time.time()})

_SCHEMA = """
CREATE TABLE IF NOT EXISTS archive_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  monument_slug TEXT,
  rights TEXT NOT NULL,
  source_note TEXT,
  script TEXT, language TEXT,
  transcription TEXT NOT NULL DEFAULT '',
  translation_en TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','reviewed')),
  image BLOB NOT NULL,
  sha256 TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS archive_claims (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id INTEGER NOT NULL REFERENCES archive_items(id) ON DELETE CASCADE,
  text TEXT NOT NULL,
  evidence_quote TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','approved','rejected')),
  reviewed_at TEXT
);
"""

_PROMPT = """You digitise photos of heritage inscriptions, plaques and manuscripts for a visitor app.
Return ONLY a JSON object with exactly these keys:
{{"script": "<writing system, e.g. Devanagari, Brahmi, Persian, Latin>",
 "language": "<language of the text>",
 "transcription": "<the text exactly as written, in its original script; empty string if you cannot read it. Never guess.>",
 "translation_en": "<English translation of the transcription; empty string if none>",
 "suggested_monument": "<one slug from the list, or null if unsure>",
 "claims": [{{"text": "<one factual statement the text supports>", "evidence_quote": "<copied verbatim from transcription or translation_en>"}}]}}
At most 5 claims. Only state what the text itself says. Valid monument slugs: {slugs}"""


def get_archive_db() -> Iterator[sqlite3.Connection]:
    raw = get_settings().archive_db_path
    path = Path(raw) if raw else BACKEND_ROOT / "data" / "archive.db"
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA)
    try:
        yield conn
    finally:
        conn.close()


def get_gemini() -> GeminiService:
    return GeminiService()


Arch = Annotated[sqlite3.Connection, Depends(get_archive_db)]
Monuments = Annotated[sqlite3.Connection, Depends(get_db)]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().casefold()


def _bad(message: str, hint: str, code: str = "VALIDATION_ERROR") -> AppError:
    return AppError(400, code, message, hint)


def _item_out(conn: sqlite3.Connection, row: sqlite3.Row, *, approved_only: bool = False) -> dict:
    q = "SELECT id, text, evidence_quote, status FROM archive_claims WHERE item_id = ?"
    if approved_only:
        q += " AND status = 'approved'"
    out = {k: row[k] for k in row.keys() if k not in ("image", "sha256")}
    out["image_url"] = f"/api/archive/items/{row['id']}/image"
    out["claims"] = [dict(c) for c in conn.execute(q + " ORDER BY id", (row["id"],))]
    return out


def _get_item(conn: sqlite3.Connection, item_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM archive_items WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        raise AppError(404, "ARCHIVE_ITEM_NOT_FOUND", "No archive item with that id.", "Check the id.")
    return row


def _slug_exists(mon: sqlite3.Connection, slug: str) -> bool:
    return mon.execute("SELECT 1 FROM monuments WHERE slug = ?", (slug,)).fetchone() is not None


def _prepare_image(data: bytes) -> bytes:
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise _bad(
            "The file could not be read as an image.", "Upload a JPEG, PNG or WebP photo.", "INVALID_FILE_TYPE"
        ) from exc
    img.thumbnail((1600, 1600))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return buf.getvalue()


def _str(d: object, key: str) -> str:
    v = d.get(key) if isinstance(d, dict) else None
    return v.strip() if isinstance(v, str) else ""


def parse_model_output(raw: str, slugs: set[str]) -> dict:
    """Parse Gemini's JSON and drop every claim whose quote is not in the text. Raises ValueError on bad JSON."""
    data = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip()))
    if not isinstance(data, dict):
        raise ValueError("not an object")
    transcription, translation = _str(data, "transcription"), _str(data, "translation_en")
    haystack = [_norm(transcription), _norm(translation)]
    claims = []
    for c in data.get("claims") if isinstance(data.get("claims"), list) else []:
        text, quote = _str(c, "text"), _str(c, "evidence_quote")
        if text and quote and any(_norm(quote) in h for h in haystack) and len(claims) < 5:
            claims.append({"text": text, "evidence_quote": quote})
    sug = data.get("suggested_monument")
    return {
        "script": _str(data, "script"),
        "language": _str(data, "language"),
        "transcription": transcription,
        "translation_en": translation,
        "claims": claims,
        "suggested_monument": sug if isinstance(sug, str) and sug in slugs else None,
    }


@router.post("/archive/digitise")
async def digitise(
    request: Request,
    photo: UploadFile,
    mon: Monuments,
    conn: Arch,
    gemini: Annotated[GeminiService, Depends(get_gemini)],
    rights: Annotated[str, Form()],
    monument_slug: Annotated[str | None, Form()] = None,
    source_note: Annotated[str | None, Form()] = None,
):
    ip = request.client.host if request.client else "unknown"
    bucket = _rate_store[ip]
    if time.time() - bucket["start"] >= _WINDOW:
        bucket.update(count=0, start=time.time())
    bucket["count"] += 1
    if bucket["count"] > _LIMIT:
        raise AppError(429, "RATE_LIMITED", "Too many digitising requests. Limit is 20 per day per IP.", "Retry tomorrow.")

    if rights not in _RIGHTS:
        raise _bad("Rights must be one of: " + ", ".join(_RIGHTS) + ".", "Say who may share this photo.")
    if source_note is not None and len(source_note) > 300:
        raise _bad("Source note is longer than 300 characters.", "Shorten the note.")
    monument_slug = monument_slug or None
    if monument_slug and not _slug_exists(mon, monument_slug):
        raise _bad(f"Unknown monument '{monument_slug}'.", "Use a monument slug such as 'qutb-complex'.")

    data = await photo.read(_MAX_BYTES + 1)  # one byte over is enough to reject it
    if len(data) > _MAX_BYTES:
        raise _bad("Photo exceeds the 6 MB limit.", "Resize the image before uploading.", "UPLOAD_TOO_LARGE")
    mime = (photo.content_type or "").split(";")[0].strip().lower()
    if mime not in _MIMES:
        raise _bad(f"Expected an image file, got '{mime}'.", "Upload a JPEG, PNG or WebP image.", "INVALID_FILE_TYPE")
    jpeg = await run_in_threadpool(_prepare_image, data)

    digest = hashlib.sha256(jpeg).hexdigest()
    existing = conn.execute("SELECT * FROM archive_items WHERE sha256 = ?", (digest,)).fetchone()
    if existing:
        return _item_out(conn, existing)

    slugs = [r["slug"] for r in mon.execute("SELECT slug FROM monuments ORDER BY slug")]
    try:
        raw = await run_in_threadpool(
            gemini.describe_image,
            jpeg,
            "image/jpeg",
            _PROMPT.format(slugs=json.dumps(slugs)),
            get_settings().llm_primary_model,
        )
        parsed = parse_model_output(raw, set(slugs))
    except (RuntimeError, ValueError) as exc:  # bad JSON is a ValueError too
        logger.warning("Archive digitise failed: %s", exc)
        raise AppError(
            503, "UPSTREAM_UNAVAILABLE", "The reading service is not available right now.", "Retry shortly."
        ) from exc

    cur = conn.execute(
        "INSERT INTO archive_items (monument_slug, rights, source_note, script, language, transcription, "
        "translation_en, image, sha256) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            monument_slug or parsed["suggested_monument"],
            rights,
            source_note,
            parsed["script"],
            parsed["language"],
            parsed["transcription"],
            parsed["translation_en"],
            jpeg,
            digest,
        ),
    )
    conn.executemany(
        "INSERT INTO archive_claims (item_id, text, evidence_quote) VALUES (?,?,?)",
        [(cur.lastrowid, c["text"], c["evidence_quote"]) for c in parsed["claims"]],
    )
    conn.commit()
    return _item_out(conn, _get_item(conn, cur.lastrowid))


@router.get("/archive/items")
def list_items(conn: Arch, status: Literal["draft", "reviewed"] | None = None, monument: str | None = None):
    q, args = "SELECT * FROM archive_items WHERE 1=1", []
    if status:
        q += " AND status = ?"
        args.append(status)
    if monument:
        q += " AND monument_slug = ?"
        args.append(monument)
    rows = conn.execute(q + " ORDER BY id DESC LIMIT 100", args).fetchall()
    return {"items": [_item_out(conn, r) for r in rows]}


@router.get("/archive/items/{item_id}")
def get_item(item_id: int, conn: Arch):
    return _item_out(conn, _get_item(conn, item_id))


@router.get("/archive/items/{item_id}/image")
def get_image(item_id: int, conn: Arch):
    return Response(
        _get_item(conn, item_id)["image"], media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"}
    )


class ClaimDecision(BaseModel):
    id: int
    decision: Literal["approve", "reject"]
    text: str | None = None


class ReviewBody(BaseModel):
    claims: list[ClaimDecision]
    monument_slug: str | None = None


@router.post("/archive/items/{item_id}/review")
def review(
    item_id: int,
    body: ReviewBody,
    conn: Arch,
    mon: Monuments,
    x_review_token: Annotated[str | None, Header()] = None,
):
    expected = get_settings().review_token
    if not expected:
        raise AppError(403, "FORBIDDEN", "Review is not enabled", "Set REVIEW_TOKEN on the server.")
    if not x_review_token or not hmac.compare_digest(x_review_token.encode(), expected.encode()):
        raise AppError(401, "UNAUTHORIZED", "Missing or wrong review token.", "Send the X-Review-Token header.")
    _get_item(conn, item_id)
    if body.monument_slug and not _slug_exists(mon, body.monument_slug):
        raise _bad(f"Unknown monument '{body.monument_slug}'.", "Use a monument slug such as 'qutb-complex'.")
    own = {r["id"] for r in conn.execute("SELECT id FROM archive_claims WHERE item_id = ?", (item_id,))}
    if any(c.id not in own for c in body.claims) or any(c.text is not None and not c.text.strip() for c in body.claims):
        raise _bad("A claim is unknown for this item or has empty text.", "Reload the item and retry.")
    for c in body.claims:
        approved = c.decision == "approve"
        conn.execute(
            "UPDATE archive_claims SET status = ?, text = COALESCE(?, text), "
            "reviewed_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id = ?",
            ("approved" if approved else "rejected", c.text.strip() if c.text and approved else None, c.id),
        )
    conn.execute(
        "UPDATE archive_items SET status = 'reviewed', monument_slug = COALESCE(?, monument_slug) WHERE id = ?",
        (body.monument_slug, item_id),
    )
    conn.commit()
    return _item_out(conn, _get_item(conn, item_id))


@router.get("/monuments/{slug}/archive")
def monument_archive(slug: str, conn: Arch, mon: Monuments):
    if not _slug_exists(mon, slug):
        raise AppError(
            404, "MONUMENT_NOT_FOUND", "No monument with that id.", "Use a monument slug such as 'qutb-complex'."
        )
    rows = conn.execute(
        "SELECT * FROM archive_items WHERE monument_slug = ? AND status = 'reviewed' AND EXISTS "
        "(SELECT 1 FROM archive_claims c WHERE c.item_id = archive_items.id AND c.status = 'approved') ORDER BY id DESC",
        (slug,),
    ).fetchall()
    return {"items": [_item_out(conn, r, approved_only=True) for r in rows]}
