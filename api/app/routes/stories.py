"""GET /api/stories/{slug} — serves pre-generated stories only, never calls Gemini."""
from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.db import get_db
from app.errors import AppError

router = APIRouter(prefix="/api/stories", tags=["stories"])


class StoryResponse(BaseModel):
    slug: str
    language: str
    story_type: str
    body: str
    audio_key: str | None
    model_version: str
    generated_at: str


@router.get("/{slug}", response_model=StoryResponse)
def get_story(
    slug: str,
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
    language: Annotated[str, Query(pattern="^(en|hi)$")] = "en",
    story_type: Annotated[str, Query(pattern="^(visitor|academic)$")] = "visitor",
) -> StoryResponse:
    """Return a pre-generated story. Raises 404 if not yet generated."""
    row = conn.execute(
        """
        SELECT m.slug, s.language, s.story_type, s.body, s.audio_key, s.model_version, s.generated_at
        FROM stories s
        JOIN monuments m ON m.id = s.monument_id
        WHERE m.slug = ? AND s.language = ? AND s.story_type = ?
        """,
        (slug, language, story_type),
    ).fetchone()

    if not row:
        raise AppError(
            404,
            "STORY_NOT_FOUND",
            f"No story found for monument '{slug}' (language={language}, type={story_type}).",
            "Run the batch generator first, or try language=en&story_type=visitor.",
        )

    return StoryResponse(
        slug=row["slug"],
        language=row["language"],
        story_type=row["story_type"],
        body=row["body"],
        audio_key=row["audio_key"],
        model_version=row["model_version"],
        generated_at=row["generated_at"],
    )