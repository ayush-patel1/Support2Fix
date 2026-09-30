"""CSRF defense for the cookie-authenticated API. See security.md §10.

Cookies are SameSite=Lax, which blocks the classic cross-site *form* POST
attack, but a same-site navigation can still carry cookies. As a second
layer, every mutating request under /api/ must carry a custom header. A
plain cross-site request (form submit, <img>, simple fetch) can't add
custom headers without triggering a CORS preflight — and preflights are
never answered here, since no CORS policy is configured (ADR-001 D10).
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CSRF_HEADER_NAME = "X-Requested-With"
CSRF_HEADER_VALUE = "support2fix"


class CsrfHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in _MUTATING_METHODS and request.url.path.startswith("/api/"):
            if request.headers.get(CSRF_HEADER_NAME) != CSRF_HEADER_VALUE:
                return JSONResponse(
                    status_code=403,
                    content={
                        "type": "about:blank",
                        "title": "csrf_header_missing",
                        "status": 403,
                        "detail": f"Missing or invalid {CSRF_HEADER_NAME} header.",
                    },
                    media_type="application/problem+json",
                )
        return await call_next(request)
