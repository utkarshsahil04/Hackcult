from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "subsystems": {
            "models": "not_implemented",
            "faiss_index": "not_implemented",
            "gemini": "configured" if settings.gemini_api_key else "missing_key",
            "database": "not_implemented",
        },
    }