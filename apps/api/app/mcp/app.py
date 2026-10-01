"""ASGI entrypoint for the `tools` process.

Run locally with:
    uvicorn app.mcp.app:app --port 8100
"""

from starlette.applications import Starlette

from app.core.config import get_settings
from app.mcp.auth import ServiceTokenMiddleware
from app.mcp.server import server


def create_app() -> Starlette:
    settings = get_settings()
    http_app = server.streamable_http_app()
    http_app.add_middleware(ServiceTokenMiddleware, token=settings.mcp_service_token)
    return http_app


app = create_app()
