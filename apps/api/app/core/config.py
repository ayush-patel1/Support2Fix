"""Application configuration, loaded from environment variables / .env.

See ../../../.env.example at the repo root for the full list of variables
and their defaults.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "support2fix-api"
    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "console"

    # Postgres connection. Async driver (asyncpg) is required — see ADR-001 D2.
    database_url: str = "postgresql+asyncpg://support2fix:support2fix@localhost:5432/support2fix"
    database_echo: bool = False

    # LLM mode — see agent-architecture.md §7.3. Not used until Phase 9, but
    # declared here so it's visible in .env.example from Phase 1 onward.
    llm_mode: Literal["live", "replay", "fake"] = "fake"
    anthropic_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor. Use as a FastAPI dependency or call directly."""
    return Settings()
