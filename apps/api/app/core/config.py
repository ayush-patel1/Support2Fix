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

    # LLM inputs leave the self-hosted installation only when both live mode
    # and explicit external-data consent are configured.
    llm_mode: Literal["live", "replay", "fake"] = "fake"
    llm_provider: Literal["gemini"] = "gemini"
    llm_model: str = "gemini-2.5-flash"
    llm_allow_external_data: bool = False
    gemini_api_key: str | None = None
    github_app_id: str | None = None
    github_app_private_key: str | None = None
    github_app_private_key_path: str | None = None
    github_api_url: str = "https://api.github.com"

    # Sessions — see security.md §10.
    session_cookie_name: str = "s2f_session"
    session_ttl_days: int = 7
    session_idle_timeout_hours: int = 12
    # None (the default) means "secure iff environment=production". A
    # Secure cookie is silently never sent back over plain http:// — not
    # just by browsers, but by httpx's client too, which is how this got
    # caught: every authenticated request after login/register came back
    # 401 in tests, because the session cookie never made it back over the
    # test transport's http:// base_url. Set this explicitly only to
    # override that default (e.g. force it on/off regardless of env).
    session_cookie_secure: bool | None = None

    @property
    def effective_session_cookie_secure(self) -> bool:
        if self.session_cookie_secure is not None:
            return self.session_cookie_secure
        return self.environment == "production"

    # `tools` (Phase 7, agent-architecture.md §5) — the MCP server process.
    # The worker authenticates to it with this shared secret, standing in
    # for the "short-lived service token" the doc describes until there's a
    # real token issuer to rotate one (a later infra phase).
    mcp_service_token: str = "dev-local-service-token"
    mcp_server_url: str = "http://localhost:8100/mcp"
    worker_poll_seconds: float = 1.0


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor. Use as a FastAPI dependency or call directly."""
    return Settings()
