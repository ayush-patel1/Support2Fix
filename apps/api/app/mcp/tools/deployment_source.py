"""MCP tools wrapping `DeploymentSource` (app/integrations/base.py)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from mcp.server.mcpserver import Context

from app.integrations.base import DeploymentSource
from app.mcp.server import server
from app.mcp.tools._common import to_jsonable, tool_adapter
from app.models.integration import IntegrationKind

_KIND = IntegrationKind.DEPLOYMENT_SOURCE


@asynccontextmanager
async def _adapter(
    ctx: Context, organization_id: str, integration_id: str
) -> AsyncIterator[DeploymentSource]:
    async with tool_adapter(
        ctx, organization_id=organization_id, integration_id=integration_id, expected_kind=_KIND
    ) as adapter:
        yield cast(DeploymentSource, adapter)


@server.tool(name="deploy.get_deployment")
async def get_deployment(
    organization_id: str, integration_id: str, version: str, ctx: Context
) -> dict[str, Any]:
    """Look up one release by version."""
    async with _adapter(ctx, organization_id, integration_id) as adapter:
        result = await adapter.get_deployment(version)
        return dict(to_jsonable(result))


@server.tool(name="deploy.list_releases")
async def list_releases(
    organization_id: str, integration_id: str, ctx: Context, limit: int = 20
) -> list[dict[str, Any]]:
    """List recent releases, newest first."""
    async with _adapter(ctx, organization_id, integration_id) as adapter:
        results = await adapter.list_releases(limit=limit)
        return list(to_jsonable(results))


@server.tool(name="deploy.get_service_version")
async def get_service_version(organization_id: str, integration_id: str, ctx: Context) -> str:
    """The version currently deployed — the newest release on record."""
    async with _adapter(ctx, organization_id, integration_id) as adapter:
        return await adapter.get_service_version()
