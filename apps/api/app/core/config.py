"""
Centralised settings loaded from .env via Pydantic Settings v2.

Why a single Settings object?  Every module imports `get_settings()` instead
of scattering `os.getenv()` calls.  Pydantic validates at startup, so a
missing DATABASE_URL is a clear error — not a mystery crash at first query.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite+aiosqlite:///./applybot.db"
    redis_url: str = "redis://localhost:6379/0"
    environment: str = "development"
    log_level: str = "debug"


@lru_cache
def get_settings() -> Settings:
    return Settings()
