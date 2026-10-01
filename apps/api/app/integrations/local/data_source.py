"""DataSource backed by a real Postgres database, connected through a

dedicated read-only role — no vendor warehouse API, no network beyond the
DB connection itself. This is the local/generic adapter for the
`DataSource` interface: it's what Support2Fix uses for shopmock today, and
what it would use for any customer's own Postgres tomorrow (same class,
different `database_url`).

The read-only boundary is enforced by Postgres itself, not by this class:
the connecting role must have `default_transaction_read_only = on` and
SELECT-only grants (see the `shopmock_readonly` role, docs/architecture/
security.md §5). `run_readonly_query` also rejects anything that isn't
syntactically a SELECT/WITH up front, purely to fail fast with a clear
error — the database, not this check, is what actually stops a write.
"""

import re
from collections.abc import Sequence
from typing import Any

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.errors import NotFoundError
from app.integrations.types import ColumnInfo, TableSchema

_READ_ONLY_STATEMENT = re.compile(r"^\s*(--[^\n]*\n\s*)*(select|with)\b", re.IGNORECASE)

_SCHEMA_QUERY = text(
    """
    SELECT table_name, column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'public'
    ORDER BY table_name, ordinal_position
    """
)

_TABLE_QUERY = text(
    """
    SELECT table_name, column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = :table_name
    ORDER BY ordinal_position
    """
)


class NotAReadOnlyStatementError(ValueError):
    pass


class LocalPostgresDataSource:
    def __init__(self, database_url: str) -> None:
        self._engine: AsyncEngine = create_async_engine(database_url, pool_pre_ping=True)

    async def aclose(self) -> None:
        await self._engine.dispose()

    async def get_schema(self) -> list[TableSchema]:
        async with self._engine.connect() as conn:
            result = await conn.execute(_SCHEMA_QUERY)
            rows = result.mappings().all()
        return self._rows_to_schemas(rows)

    async def describe_table(self, table: str) -> TableSchema:
        async with self._engine.connect() as conn:
            result = await conn.execute(_TABLE_QUERY, {"table_name": table})
            rows = result.mappings().all()
        if not rows:
            raise NotFoundError(f"No table named {table!r} in the public schema.")
        return self._rows_to_schemas(rows)[0]

    def _rows_to_schemas(self, rows: Sequence[RowMapping]) -> list[TableSchema]:
        tables: dict[str, list[ColumnInfo]] = {}
        for row in rows:
            tables.setdefault(row["table_name"], []).append(
                ColumnInfo(
                    name=row["column_name"],
                    data_type=row["data_type"],
                    nullable=row["is_nullable"] == "YES",
                )
            )
        return [TableSchema(name=name, columns=columns) for name, columns in tables.items()]

    async def run_readonly_query(
        self, sql: str, *, params: dict[str, Any] | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        if not _READ_ONLY_STATEMENT.match(sql):
            raise NotAReadOnlyStatementError(
                "run_readonly_query only accepts a SELECT or WITH statement."
            )
        async with self._engine.connect() as conn:
            result = await conn.execute(text(sql), params or {})
            rows = result.mappings().fetchmany(limit)
        return [dict(row) for row in rows]
