"""MCP tools wrapping `CodeHost` (app/integrations/base.py)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from mcp.server.mcpserver import Context

from app.integrations.base import CodeHost
from app.mcp.server import server
from app.mcp.tools._common import to_jsonable, tool_adapter
from app.models.integration import IntegrationKind

_KIND = IntegrationKind.CODE_HOST


@asynccontextmanager
async def _adapter(
    ctx: Context, organization_id: str, integration_id: str
) -> AsyncIterator[CodeHost]:
    async with tool_adapter(
        ctx, organization_id=organization_id, integration_id=integration_id, expected_kind=_KIND
    ) as adapter:
        yield cast(CodeHost, adapter)


@server.tool(name="code.search_code")
async def search_code(
    organization_id: str, integration_id: str, query: str, ctx: Context, limit: int = 20
) -> list[dict[str, Any]]:
    """Search a service's source code for a literal string."""
    async with _adapter(ctx, organization_id, integration_id) as adapter:
        results = await adapter.search_code(query, limit=limit)
        return list(to_jsonable(results))


@server.tool(name="code.get_file")
async def get_file(
    organization_id: str, integration_id: str, path: str, ctx: Context, ref: str | None = None
) -> dict[str, Any]:
    """Read one file's full content at a given ref (default: the default branch's HEAD)."""
    async with _adapter(ctx, organization_id, integration_id) as adapter:
        result = await adapter.get_file(path, ref=ref)
        return dict(to_jsonable(result))


@server.tool(name="code.get_commit")
async def get_commit(
    organization_id: str, integration_id: str, sha: str, ctx: Context
) -> dict[str, Any]:
    """Look up one commit by SHA: message, author, timestamp, files changed."""
    async with _adapter(ctx, organization_id, integration_id) as adapter:
        result = await adapter.get_commit(sha)
        return dict(to_jsonable(result))


@server.tool(name="code.list_commits")
async def list_commits(
    organization_id: str,
    integration_id: str,
    ctx: Context,
    path: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List recent commits, optionally restricted to one file's history."""
    async with _adapter(ctx, organization_id, integration_id) as adapter:
        results = await adapter.list_commits(path=path, limit=limit)
        return list(to_jsonable(results))


@server.tool(name="code.create_branch")
async def create_branch(
    organization_id: str, integration_id: str, name: str, ctx: Context, base: str = "main"
) -> dict[str, Any]:
    """Create a new branch from `base` — the first step before proposing a fix."""
    async with _adapter(ctx, organization_id, integration_id) as adapter:
        result = await adapter.create_branch(name, base=base)
        return dict(to_jsonable(result))


@server.tool(name="code.create_pull_request")
async def create_pull_request(
    organization_id: str,
    integration_id: str,
    branch: str,
    base: str,
    title: str,
    description: str,
    ctx: Context,
) -> dict[str, Any]:
    """Open a pull request. Not implemented for the local git adapter

    (a PR is a hosted-platform concept) — raises a clear tool error until
    the GitHub adapter (Phase 15) exists.
    """
    async with _adapter(ctx, organization_id, integration_id) as adapter:
        result = await adapter.create_pull_request(
            branch=branch, base=base, title=title, description=description
        )
        return dict(to_jsonable(result))
