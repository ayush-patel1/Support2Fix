"""The `tools` MCP server (agent-architecture.md §5, system-design.md §2):

wraps the five Phase 6 integration interfaces as MCP tools over streamable
HTTP. The worker (Phase 9+) is the only intended client, reaching this
process through the ToolGateway (Phase 8) — there is no ToolGateway yet, so
every tool here takes `organization_id`/`integration_id` as plain arguments
rather than having them injected from a trusted investigation context. That
trust boundary moves to the gateway once it exists; this process still
re-derives the Integration row from the database on every call and refuses
one from another organization or of the wrong kind, so it is never just
trusting whatever the caller claims.
"""

from mcp.server.mcpserver import MCPServer

from app.mcp.context import app_lifespan

server: MCPServer[object] = MCPServer(
    name="support2fix-tools",
    instructions=(
        "Tools for investigating a Support2Fix customer's environment: source code, "
        "application logs, the customer's own database (read-only), deployment history, "
        "and the platform's own ticket/customer records. Every tool takes organization_id "
        "and integration_id identifying which configured Integration to use."
    ),
    lifespan=app_lifespan,
)

# Each module registers its tools on `server` as a side effect of import.
from app.mcp.tools import (  # noqa: E402  (must follow `server`'s creation above)
    code_host,
    data_source,
    deployment_source,
    log_source,
    support_source,
)

__all__ = [
    "server",
    "code_host",
    "data_source",
    "deployment_source",
    "log_source",
    "support_source",
]
