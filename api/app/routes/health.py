import sqlite3
from contextlib import closing
from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import get_settings
from app.db import resolve_db_path
from app.ml import RecognitionPipeline, get_pipeline

router = APIRouter(prefix="/api")


def _database_status() -> str:
    path = resolve_db_path()
    if not path.is_file():
        return "missing"
    try:
        with closing(sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)) as conn:
            conn.execute("SELECT 1 FROM monuments LIMIT 1").fetchone()
    except sqlite3.Error:
        return "error"
    return "ok"


@router.get("/health")
def health(pipeline: Annotated[RecognitionPipeline, Depends(get_pipeline)]):
    settings = get_settings()
    pipeline_status = pipeline.status()
    return {
        "status": "ok",
        "subsystems": {
            "models": pipeline_status.models,
            "faiss_index": pipeline_status.faiss_index,
            "gemini": "configured" if settings.gemini_api_key else "missing_key",
            "database": _database_status(),
        },
    }
