from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

API_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    # The root .env is the one to use. api/.env still works and wins, for existing setups.
    model_config = SettingsConfigDict(
        env_file=(API_ROOT.parent / ".env", API_ROOT / ".env"),
        env_ignore_empty=True,
        extra="ignore",
    )

    gemini_api_key: str
    ors_api_key: str = ""
    frontend_origin: str = "http://localhost:3000"
    database_url: str | None = None
    sqlite_db_path: str | None = None
    llm_primary_model: str = "gemini-3.5-flash-lite"
    redis_url: str | None = None
    demo_mode: bool = False
    offline_mode: bool = False

    @field_validator("gemini_api_key")
    @classmethod
    def key_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("GEMINI_API_KEY is empty. Set it in .env")
        return v.strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()
