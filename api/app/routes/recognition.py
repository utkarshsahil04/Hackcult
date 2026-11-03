"""POST /api/recognition/identify and demo photo helpers (Issue #17).

- Accepts a resized photo (multipart/form-data, field name: photo)
- Per-IP in-memory rate limit: 30 requests / day
- Max upload size: 6 MB
- Non-image files rejected with 400
- Demo photos return deterministic high-confidence cached candidates
- Uncertain match  → 200 with candidates list (never a 500)
- Model failure    → 500 in the error envelope (never looks like uncertain)
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, UploadFile
from fastapi.responses import JSONResponse

from app.demo_cache import get_demo_cache
from app.errors import AppError
from app.ml import Candidate, get_pipeline

logger = logging.getLogger("raahein.api")

router = APIRouter(prefix="/api")

# ── Rate limit store ──────────────────────────────────────────────────────────
# { ip: {"count": int, "window_start": float} }
# Resets per-IP when a new calendar day begins (86 400 s window).
_rate_store: dict[str, dict] = defaultdict(lambda: {"count": 0, "window_start": time.time()})

_WINDOW = 86_400  # seconds in a day
_LIMIT = 30  # requests per window per IP
_MAX_BYTES = 6 * 1024 * 1024  # 6 MB
_ALLOWED_PREFIXES = (
    b"\xff\xd8",  # JPEG
    b"\x89PNG",  # PNG
    b"GIF8",  # GIF
    b"RIFF",  # WEBP (RIFF....WEBP)
    b"\x00\x00\x00",  # possible MP4/HEIC — rejected below by mime
)
_ALLOWED_MIMES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    bucket = _rate_store[ip]
    if now - bucket["window_start"] >= _WINDOW:
        bucket["count"] = 0
        bucket["window_start"] = now
    bucket["count"] += 1
    if bucket["count"] > _LIMIT:
        raise AppError(
            429,
            "RATE_LIMITED",
            "Too many recognition requests. Limit is 30 per day per IP.",
            "Retry after midnight UTC.",
        )


def _validate_image(file: UploadFile, data: bytes) -> None:
    # Size
    if len(data) > _MAX_BYTES:
        raise AppError(
            400,
            "UPLOAD_TOO_LARGE",
            f"Photo exceeds the {_MAX_BYTES // (1024 * 1024)} MB limit.",
            "Resize the image to under 1024 px before uploading.",
        )
    # MIME type declared by the client
    mime = (file.content_type or "").split(";")[0].strip().lower()
    if mime not in _ALLOWED_MIMES:
        raise AppError(
            400,
            "INVALID_FILE_TYPE",
            f"Expected an image file, got '{mime}'.",
            "Upload a JPEG, PNG, GIF or WebP image.",
        )
    # Magic bytes (defence-in-depth against a wrong Content-Type)
    if not any(data[:4].startswith(p[:4]) for p in _ALLOWED_PREFIXES[:4]):
        raise AppError(
            400,
            "INVALID_FILE_TYPE",
            "File contents do not look like an image.",
            "Upload a JPEG, PNG, GIF or WebP image.",
        )


def _candidate_dict(c: Candidate) -> dict:
    return {"slug": c.slug, "name": c.name, "score": round(c.score, 4)}


@router.post("/recognition/identify")
async def identify(
    request: Request,
    photo: UploadFile,
    pipeline: Annotated[object, Depends(get_pipeline)],
):
    ip = request.client.host if request.client else "unknown"
    _check_rate_limit(ip)

    data = await photo.read()
    _validate_image(photo, data)

    try:
        result = pipeline.run(data)
        if result.status == "error":
            raise AppError(
                500,
                "RECOGNITION_ERROR",
                "The recognition model failed to process the photo.",
                "Retry shortly. If the problem persists, contact support.",
            )
    except Exception as exc:
        if isinstance(exc, AppError):
            raise
        logger.exception("Recognition pipeline error", exc_info=exc)
        raise AppError(
            500,
            "RECOGNITION_ERROR",
            "The recognition model failed to process the photo.",
            "Retry shortly. If the problem persists, contact support.",
        ) from exc

    content = {
        "status": result.status,  # "ok" | "uncertain"
        "candidates": [_candidate_dict(c) for c in result.candidates],
    }
    if hasattr(result, "provenance") and result.provenance:
        content["source"] = result.provenance

    # Uncertain is a valid answer, not an error → always 200
    return JSONResponse(
        status_code=200,
        content=content,
    )


@router.get("/recognition/demo-photos")
def list_demo_photos():
    """List the 5 pre-cached demo photos available for offline demonstration."""
    cache = get_demo_cache()
    return {"photos": cache.list_photos()}


@router.get("/recognition/demo-photos/{slug_or_filename}")
def get_demo_photo(slug_or_filename: str):
    """Retrieve raw image bytes of an official demo photo."""
    cache = get_demo_cache()
    res = cache.get_photo_bytes(slug_or_filename)
    if not res:
        raise AppError(
            404,
            "DEMO_PHOTO_NOT_FOUND",
            f"No demo photo found for '{slug_or_filename}'.",
            "Use one of: taj_mahal.jpg, qutb_minar.jpg, humayuns_tomb.jpg, red_fort.jpg, agra_fort.jpg.",
        )
    data, media_type = res
    return Response(content=data, media_type=media_type)
