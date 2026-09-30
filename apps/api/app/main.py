"""FastAPI application factory and entrypoint.

Run locally with:
    uvicorn app.main:app --reload --port 8000
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.csrf import CsrfHeaderMiddleware
from app.core.db import dispose_engine, init_engine
from app.core.errors import AppError
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    configure_logging(settings)
    init_engine(settings.database_url, echo=settings.database_echo)
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Support2Fix API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(CsrfHeaderMiddleware)

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": "about:blank",
                "title": exc.code,
                "status": exc.status_code,
                "detail": exc.message,
            },
            media_type="application/problem+json",
        )

    @app.get("/health", tags=["health"])
    async def liveness() -> dict[str, str]:
        """Pure liveness probe: the process is up. No dependency checks.

        Readiness (including the database) is /api/v1/health.
        """
        return {"status": "ok"}

    app.include_router(api_v1_router)
    return app


app = create_app()
