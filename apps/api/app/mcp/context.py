"""The `tools` process's own lifespan — a separate runtime unit from `api`

(system-design.md §2: same codebase/image, different start command), so it
owns its own DB engine rather than reusing one initialized elsewhere.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.db import dispose_engine, get_engine, init_engine


@dataclass
class AppContext:
    session_factory: async_sessionmaker[AsyncSession]


@asynccontextmanager
async def app_lifespan(_server: Any) -> AsyncIterator[AppContext]:
    settings = get_settings()
    init_engine(settings.database_url, echo=settings.database_echo)
    try:
        yield AppContext(session_factory=async_sessionmaker(get_engine(), expire_on_commit=False))
    finally:
        await dispose_engine()
