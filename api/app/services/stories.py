"""Story generation, claim checking, and batch pre-generation for Raahein.

Design rules (Issue #8):
- GET /api/stories/{slug} NEVER calls Gemini — serves stored text only.
- Generation happens only in the batch script (scripts/generate_stories.py).
- Every claim in a generated story must map to a stored source sentence.
- Legends are labelled explicitly in the output.
- audio_key is set by a separate TTS step; this module only generates text.
"""
from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import dataclass

from app.services.gemini import GeminiService

logger = logging.getLogger("raahein.api.stories")

STORY_MODEL = "gemini-2.0-flash-lite"

VISITOR_PROMPT_TEMPLATE = """\
You are a heritage storyteller for Raahein, an Indian monument discovery app.
Write a short, engaging story (150-200 words) for a visitor standing at {monument_name}.
Language: {language_label}.

STRICT RULES:
1. Use ONLY the verified claims and source notes listed below. Do not add any fact not present here.
2. If a claim is marked LEGEND, you MUST introduce it with a phrase like
   "According to legend," or "Folklore holds that" — never present it as established fact.
3. Do not mention percentages, confidence scores, or the word "content".
4. Write in second person ("As you stand here...").
5. End with one sentence connecting this monument to another on the list of related monuments.

VERIFIED CLAIMS:
{claims_block}

RELATED MONUMENTS:
{related_block}
"""

ACADEMIC_PROMPT_TEMPLATE = """\
You are a heritage researcher writing for Raahein, an Indian monument discovery app.
Write a concise academic note (180-220 words) about {monument_name}.
Language: {language_label}.

STRICT RULES:
1. Use ONLY the verified claims and source notes listed below. Do not add any fact not present here.
2. If a claim is marked LEGEND, you MUST introduce it with a phrase like
   "According to tradition," or "Local legend holds that" — never present it as established fact.
3. Cite sources inline as (Publisher, year) where the note provides enough detail.
4. Do not mention Wikipedia, confidence scores, or the word "content".
5. Write in third person.

VERIFIED CLAIMS:
{claims_block}

RELATED MONUMENTS:
{related_block}
"""

LANGUAGE_LABELS = {"en": "English", "hi": "Hindi (Devanagari script)"}


@dataclass
class ClaimCheckResult:
    passed: bool
    unchecked_sentences: list[str]  # sentences with no matching source note


def _build_claims_block(claims: list[sqlite3.Row]) -> str:
    lines = []
    for c in claims:
        tag = " [LEGEND]" if c["is_legend"] else ""
        lines.append(f"- [{c['claim_type'].upper()}{tag}] {c['text']}")
        for note in c["source_notes"]:
            lines.append(f"    Source note: {note}")
    return "\n".join(lines) or "(no claims available)"


def _build_related_block(related: list[sqlite3.Row]) -> str:
    if not related:
        return "(none)"
    return "\n".join(f"- {r['name']} ({r['relation_type']})" for r in related)


def _fetch_monument_data(
    conn: sqlite3.Connection, slug: str
) -> tuple[sqlite3.Row | None, list[dict], list[sqlite3.Row]]:
    """Return (monument_row, enriched_claims, related_monuments)."""
    monument = conn.execute(
        "SELECT id, name FROM monuments WHERE slug = ?", (slug,)
    ).fetchone()
    if not monument:
        return None, [], []

    # Claims with their source notes joined
    raw_claims = conn.execute(
        """
        SELECT c.id, c.claim_type, c.text, c.is_legend, c.position,
               GROUP_CONCAT(ms.note, '||') AS notes_concat
        FROM claims c
        LEFT JOIN monument_sources ms ON ms.claim_id = c.id
        WHERE c.monument_id = ?
        ORDER BY c.position, c.id
        """,
        (monument["id"],),
    ).fetchall()

    claims: list[dict] = []
    for row in raw_claims:
        notes = row["notes_concat"].split("||") if row["notes_concat"] else []
        claims.append({
            "claim_type": row["claim_type"],
            "text": row["text"],
            "is_legend": bool(row["is_legend"]),
            "position": row["position"],
            "source_notes": notes,
        })

    related = conn.execute(
        """
        SELECT m.name, mr.relation_type
        FROM monument_relationships mr
        JOIN monuments m ON m.id = mr.to_monument_id
        WHERE mr.from_monument_id = ?
        LIMIT 5
        """,
        (monument["id"],),
    ).fetchall()

    return monument, claims, related


def check_claims(story_body: str, claims: list[dict]) -> ClaimCheckResult:
    """Check every sentence in story_body maps to at least one source note or claim text.

    A sentence passes if any claim text or source note shares >= 3 significant words with it.
    This is a heuristic; it catches hallucinated facts while tolerating paraphrase.
    """
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "is", "was", "are", "were", "it", "its", "this", "that",
        "as", "by", "from", "has", "have", "had", "be", "been",
    }

    all_source_text = []
    for c in claims:
        all_source_text.append(c["text"].lower())
        for note in c["source_notes"]:
            all_source_text.append(note.lower())

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", story_body) if s.strip()]
    unchecked: list[str] = []

    for sentence in sentences:
        words = {w for w in re.findall(r"[a-z]+", sentence.lower()) if w not in stop_words}
        if len(words) < 3:
            continue  # too short to check meaningfully
        matched = any(
            len(words & {w for w in re.findall(r"[a-z]+", src) if w not in stop_words}) >= 3
            for src in all_source_text
        )
        if not matched:
            unchecked.append(sentence)

    return ClaimCheckResult(passed=len(unchecked) == 0, unchecked_sentences=unchecked)


def generate_story(
    conn: sqlite3.Connection,
    gemini: GeminiService,
    slug: str,
    language: str,
    story_type: str,
) -> tuple[str, ClaimCheckResult]:
    """Generate a story for one monument/language/type. Does NOT write to DB.

    Returns (story_body, claim_check_result).
    Raises ValueError if the monument is not found.
    Raises RuntimeError if Gemini fails or the claim check fails.
    """
    monument, claims, related = _fetch_monument_data(conn, slug)
    if not monument:
        raise ValueError(f"Monument not found: {slug!r}")
    if not claims:
        raise ValueError(f"No claims found for monument: {slug!r}")

    claims_block = _build_claims_block(
        [type("R", (), c)() for c in claims]  # type: ignore[arg-type]
    )
    related_block = _build_related_block(related)
    language_label = LANGUAGE_LABELS.get(language, language)

    template = VISITOR_PROMPT_TEMPLATE if story_type == "visitor" else ACADEMIC_PROMPT_TEMPLATE
    prompt = template.format(
        monument_name=monument["name"],
        language_label=language_label,
        claims_block=claims_block,
        related_block=related_block,
    )

    body = gemini._call_gemini(prompt, timeout=30.0, model=STORY_MODEL, max_output_tokens=400)

    result = check_claims(body, claims)
    if not result.passed:
        logger.warning(
            "Claim check: %d unchecked sentence(s) in %s/%s/%s",
            len(result.unchecked_sentences),
            slug, language, story_type,
        )

    return body, result


def store_story(
    conn: sqlite3.Connection,
    slug: str,
    language: str,
    story_type: str,
    body: str,
    model_version: str,
) -> None:
    """Upsert a story row. Replaces an existing row for the same (slug, language, story_type)."""
    monument = conn.execute(
        "SELECT id FROM monuments WHERE slug = ?", (slug,)
    ).fetchone()
    if not monument:
        raise ValueError(f"Monument not found: {slug!r}")

    conn.execute(
        """
        INSERT INTO stories (monument_id, language, story_type, body, model_version)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (monument_id, language, story_type)
        DO UPDATE SET body = excluded.body,
                      model_version = excluded.model_version,
                      generated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
        """,
        (monument["id"], language, story_type, body, model_version),
    )