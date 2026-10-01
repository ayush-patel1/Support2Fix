"""MCP tools wrapping `DataSource` (app/integrations/base.py)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from mcp.server.mcpserver import Context

from app.integrations.base import DataSource
from app.mcp.server import server
from app.mcp.tools._common import to_jsonable, tool_adapter
from app.models.integration import IntegrationKind

_KIND = IntegrationKind.DATA_SOURCE


@asynccontextmanager
async def _adapter(
    ctx: Context, organization_id: str, integration_id: str
) -> AsyncIterator[DataSource]:
    async with tool_adapter(
        ctx, organization_id=organization_id, integration_id=integration_id, expected_kind=_KIND
    ) as adapter:
        yield cast(DataSource, adapter)


@server.tool(name="data.get_schema")
async def get_schema(
    organization_id: str, integration_id: str, ctx: Context
) -> list[dict[str, Any]]:
    """List every table in the customer's database and its columns."""
    async with _adapter(ctx, organization_id, integration_id) as adapter:
        results = await adapter.get_schema()
        return list(to_jsonable(results))


@server.tool(name="data.describe_table")
async def describe_table(
    organization_id: str, integration_id: str, table: str, ctx: Context
) -> dict[str, Any]:
    """Describe one table's columns, types and nullability."""
    async with _adapter(ctx, organization_id, integration_id) as adapter:
        result = await adapter.describe_table(table)
        return dict(to_jsonable(result))


@server.tool(name="data.run_readonly_query")
async def run_readonly_query(
    organization_id: str,
    integration_id: str,
    sql: str,
    ctx: Context,
    params: dict[str, Any] | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Run a read-only SELECT/WITH query against the customer's database.

    The query must be a SELECT or WITH statement — enforced here for a fast,
    clear error, and independently enforced by the database itself through
    a role with `default_transaction_read_only = on` (security.md §5).
    """
    async with _adapter(ctx, organization_id, integration_id) as adapter:
        rows = await adapter.run_readonly_query(sql, params=params, limit=limit)
        return list(to_jsonable(rows))
