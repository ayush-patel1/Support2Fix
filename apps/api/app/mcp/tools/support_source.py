"""MCP tools wrapping `SupportSource` (app/integrations/base.py).

Unlike the other four kinds, this one wraps the platform's own ticket
system rather than an external target — see
app/integrations/local/support_source.py.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from mcp.server.mcpserver import Context

from app.integrations.base import SupportSource
from app.mcp.server import server
from app.mcp.tools._common import to_jsonable, tool_adapter
from app.models.integration import IntegrationKind

_KIND = IntegrationKind.SUPPORT_SOURCE


@asynccontextmanager
async def _adapter(
    ctx: Context, organization_id: str, integration_id: str
) -> AsyncIterator[SupportSource]:
    async with tool_adapter(
        ctx, organization_id=organization_id, integration_id=integration_id, expected_kind=_KIND
    ) as adapter:
        yield cast(SupportSource, adapter)


@server.tool(name="support.get_ticket")
async def get_ticket(
    organization_id: str, integration_id: str, ticket_id: str, ctx: Context
) -> dict[str, Any]:
    """Fetch a Support2Fix ticket by id."""
    async with _adapter(ctx, organization_id, integration_id) as adapter:
        result = await adapter.get_ticket(ticket_id)
        return dict(to_jsonable(result))


@server.tool(name="support.get_customer")
async def get_customer(
    organization_id: str, integration_id: str, customer_id: str, ctx: Context
) -> dict[str, Any]:
    """Fetch a Support2Fix customer by id."""
    async with _adapter(ctx, organization_id, integration_id) as adapter:
        result = await adapter.get_customer(customer_id)
        return dict(to_jsonable(result))
