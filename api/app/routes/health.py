from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import get_settings
from app.ml import RecognitionPipeline, get_pipeline

router = APIRouter(prefix="/api")


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
            "database": "not_implemented",
        },
    }