from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str
    ors_api_key: str = ""
    frontend_origin: str = "http://localhost:3000"
    database_url: str | None = None
    redis_url: str | None = None

    @field_validator("gemini_api_key")
    @classmethod
    def key_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("GEMINI_API_KEY is empty. Set it in api/.env")
        return v.strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()