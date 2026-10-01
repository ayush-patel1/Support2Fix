"""MCP tools wrapping `LogSource` (app/integrations/base.py)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, cast

from mcp.server.mcpserver import Context

from app.integrations.base import LogSource
from app.mcp.server import server
from app.mcp.tools._common import to_jsonable, tool_adapter
from app.models.integration import IntegrationKind

_KIND = IntegrationKind.LOG_SOURCE


@asynccontextmanager
async def _adapter(
    ctx: Context, organization_id: str, integration_id: str
) -> AsyncIterator[LogSource]:
    async with tool_adapter(
        ctx, organization_id=organization_id, integration_id=integration_id, expected_kind=_KIND
    ) as adapter:
        yield cast(LogSource, adapter)


@server.tool(name="logs.search_logs")
async def search_logs(
    organization_id: str,
    integration_id: str,
    query: str,
    ctx: Context,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Search application logs for a service within an optional time window."""
    async with _adapter(ctx, organization_id, integration_id) as adapter:
        results = await adapter.search(query, since=since, until=until, limit=limit)
        return list(to_jsonable(results))


@server.tool(name="logs.get_event")
async def get_event(
    organization_id: str, integration_id: str, event_id: str, ctx: Context
) -> dict[str, Any]:
    """Fetch one log event by id, e.g. an id returned by `logs.search_logs`."""
    async with _adapter(ctx, organization_id, integration_id) as adapter:
        result = await adapter.get_event(event_id)
        return dict(to_jsonable(result))
