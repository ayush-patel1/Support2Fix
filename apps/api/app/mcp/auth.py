"""Service-token auth for the `tools` process — the "short-lived service

token" agent-architecture.md §5 describes the worker authenticating to MCP
servers with. This is a static shared secret, not an actual short-lived,
rotating token: there's no token issuer yet (that needs real deployment
infra — a later phase), and the only client today is this Phase's own
smoke test, not the worker (Phase 9+). Same shape as `CsrfHeaderMiddleware`
(app/core/csrf.py): one header check, fail closed.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

SERVICE_TOKEN_HEADER = "Authorization"


class ServiceTokenMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, token: str) -> None:
        super().__init__(app)
        self._expected = f"Bearer {token}"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.headers.get(SERVICE_TOKEN_HEADER) != self._expected:
            return JSONResponse(
                status_code=401, content={"error": "invalid or missing service token"}
            )
        return await call_next(request)
