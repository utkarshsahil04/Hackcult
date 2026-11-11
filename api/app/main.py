import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from app.body_limit import BodyLimitMiddleware
from app.config import get_settings
from app.errors import register_error_handlers
from app.ml import get_pipeline
from app.routes import archive, health, monuments, places, recognition, stories, tours

settings = get_settings()  # fails fast at startup if env is invalid


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Warm the models so the first visitor photo is not a 30 s cold start. A failed load is
    # reported by /api/health and surfaces as a 500 on identify, never as "uncertain".
    try:
        await run_in_threadpool(get_pipeline().load)
    except Exception:  # noqa: BLE001
        logging.getLogger("raahein.api").warning("Recognition pipeline not loaded at startup")
    yield


app = FastAPI(title="Raahein API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(BodyLimitMiddleware)
register_error_handlers(app)
app.include_router(health.router)
app.include_router(monuments.router)
app.include_router(places.router)
app.include_router(recognition.router)
app.include_router(tours.router)
app.include_router(stories.router)
app.include_router(archive.router)
