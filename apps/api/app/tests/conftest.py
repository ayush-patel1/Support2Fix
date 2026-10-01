import os
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import create_app

CSRF_HEADERS = {"X-Requested-With": "support2fix"}

# A dedicated test database, separate from local dev — see README.md. Tests
# that need it (test_auth.py, test_organizations.py, via the `db_app` /
# `db_client` fixtures) skip with a clear reason if it isn't reachable,
# rather than failing the whole suite.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://support2fix:support2fix@localhost:5432/support2fix_test",
)

# Filled in on the first failed connection attempt, so every later DB test
# skips immediately instead of each waiting out its own connection failure
# (~4s apiece on Windows — over a minute for the suite without this).
_db_skip_reason: dict[str, str] = {}


@pytest.fixture
async def client():
    """An ASGI test client. No real Postgres is required: the /health

    liveness check does not touch the database, and /api/v1/health degrades
    gracefully (status 503, database: "unreachable") when it can't connect
    instead of raising — see test_health.py.
    """
    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
async def db_app(monkeypatch):
    """A running app wired to TEST_DATABASE_URL, with tables created and

    emptied between tests (schema is created once per database, then left
    in place — see the `truncate` step below). Yields the FastAPI `app`
    object itself (not a client) so tests that need *two* independently
    logged-in identities can open a second AsyncClient against the same
    app/engine — see test_organizations.py's cross-tenant tests.
    """
    from app.core.config import get_settings
    from app.core.db import Base, get_engine

    if "reason" in _db_skip_reason:
        pytest.skip(_db_skip_reason["reason"])

    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    get_settings.cache_clear()

    app = create_app()
    try:
        async with app.router.lifespan_context(app):
            engine = get_engine()
            try:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
            except Exception as exc:  # any connection/setup failure means "skip this suite"
                _db_skip_reason["reason"] = (
                    f"TEST_DATABASE_URL not reachable ({TEST_DATABASE_URL}): {exc}"
                )
                pytest.skip(_db_skip_reason["reason"])

            yield app

            async with engine.begin() as conn:
                for table in reversed(Base.metadata.sorted_tables):
                    await conn.execute(table.delete())
    finally:
        get_settings.cache_clear()


@pytest.fixture
async def db_client(db_app: FastAPI):
    transport = ASGITransport(app=db_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def new_client(app: FastAPI) -> AsyncClient:
    """A second, independent identity (its own cookie jar) against the same

    running app/engine as `db_client` — for tests involving two users.
    """
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


MCP_TEST_BASE_URL = "http://127.0.0.1:9999"  # port is arbitrary; matches the
# SDK's "127.0.0.1:*" auto-allowed Host pattern for its DNS-rebinding check
# (lowlevel/server.py's streamable_http_app) — a made-up hostname like
# "mcp-test" gets rejected before a request is even routed.


@asynccontextmanager
async def mcp_test_session(monkeypatch: pytest.MonkeyPatch):
    """The Phase 7 `tools` app, end to end: real DB-backed tables, a real

    `ClientSession` over a real (in-process) streamable-HTTP transport. A
    plain async context manager, not a pytest fixture: the MCP session
    manager owns an anyio task group for the lifetime of its lifespan
    (streamable_http_manager.py), and that task group's cancel scope must
    be entered and exited by the *same* asyncio task — true inside one
    `async with` in a test body, not guaranteed across a fixture's
    setup/yield/teardown boundaries under pytest-asyncio.

    Usage: `async with mcp_test_session(monkeypatch) as (session, engine): ...`
    """
    import httpx2
    from mcp.client.session import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    from app.core.config import get_settings
    from app.core.db import Base, get_engine
    from app.mcp.app import create_app as create_mcp_app

    if "reason" in _db_skip_reason:
        pytest.skip(_db_skip_reason["reason"])

    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    get_settings.cache_clear()

    app = create_mcp_app()
    try:
        async with app.router.lifespan_context(app):
            engine = get_engine()
            try:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
            except Exception as exc:
                _db_skip_reason["reason"] = (
                    f"TEST_DATABASE_URL not reachable ({TEST_DATABASE_URL}): {exc}"
                )
                pytest.skip(_db_skip_reason["reason"])

            http_client = httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=app),
                base_url=MCP_TEST_BASE_URL,
                headers={"Authorization": f"Bearer {get_settings().mcp_service_token}"},
            )
            async with http_client:
                async with streamable_http_client(
                    f"{MCP_TEST_BASE_URL}/mcp", http_client=http_client
                ) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        yield session, engine

            async with engine.begin() as conn:
                for table in reversed(Base.metadata.sorted_tables):
                    await conn.execute(table.delete())
    finally:
        get_settings.cache_clear()
