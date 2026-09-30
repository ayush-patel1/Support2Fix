"""Shopmock's own database — separate from the platform's. Support2Fix will

eventually connect to this the same way it would connect to any customer's
database: read-only, from the outside (see security.md §5 on
`run_readonly_query`'s dedicated-role boundary). That integration is Phase
6+; for now this module just runs the mock shop itself.
"""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.environ.get(
    "SHOPMOCK_DATABASE_URL",
    "postgresql+asyncpg://support2fix:support2fix@localhost:5432/shopmock",
)


class Base(DeclarativeBase):
    __mapper_args__ = {"eager_defaults": True}


engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
