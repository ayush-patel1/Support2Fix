"""ASGI entrypoint for the `tools` process.

Run locally with:
    uvicorn app.mcp.app:app --port 8100
"""

from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette

from app.core.config import get_settings
from app.mcp.auth import ServiceTokenMiddleware
from app.mcp.server import server


def create_app() -> Starlette:
    settings = get_settings()
    http_app = server.streamable_http_app(
        transport_security=TransportSecuritySettings(
            allowed_hosts=["127.0.0.1:*", "localhost:8100", "tools:8100"]
        )
    )
    http_app.add_middleware(ServiceTokenMiddleware, token=settings.mcp_service_token)
    return http_app


app = create_app()
