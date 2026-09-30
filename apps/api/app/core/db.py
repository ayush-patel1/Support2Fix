"""Async SQLAlchemy engine, session factory, and the DB dependency.

One engine per process, created lazily from settings. See system-design.md
§6 for the data model and the tenant-isolation rules that repositories
built on `get_db` must follow (added from Phase 2 onward).
"""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models. Alembic's env.py targets this metadata.

    `eager_defaults=True` makes every model fetch server-computed columns
    (created_at/updated_at's `server_default`/`onupdate=func.now()`) back via
    `RETURNING` as part of the same INSERT/UPDATE, instead of leaving them
    marked stale until something reads them. Async sessions can't satisfy a
    stale-attribute lazy-load implicitly (there's no event loop to hop into
    from a synchronous attribute access), so without this, serializing a
    just-updated row — e.g. `TicketPublic.model_validate(ticket)` right
    after `change_status()` commits — fails with `MissingGreenlet`. Applies
    to every subclass (a plain class-level dict on a non-polymorphic base is
    inherited by each mapped subclass's own mapper configuration).
    """

    __mapper_args__ = {"eager_defaults": True}


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    global _engine, _session_factory
    _engine = create_async_engine(database_url, echo=echo, pool_pre_ping=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call init_engine() first.")
    return _engine


async def dispose_engine() -> None:
    if _engine is not None:
        await _engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped session."""
    if _session_factory is None:
        raise RuntimeError("Database engine not initialized. Call init_engine() first.")
    async with _session_factory() as session:
        yield session


async def ping_db() -> bool:
    """Used by the readiness check. Returns False instead of raising."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
