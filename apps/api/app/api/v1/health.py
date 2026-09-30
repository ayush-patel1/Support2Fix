"""Versioned health endpoint.

Unlike the unversioned /health (pure liveness, see app/main.py), this one
checks the database and is meant for readiness probes and for the frontend
to confirm the API stack is actually usable.
"""

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from app.core.db import ping_db

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    status: str
    database: str


@router.get("/health", response_model=HealthStatus)
async def health(response: Response) -> HealthStatus:
    db_ok = await ping_db()
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthStatus(
        status="ok" if db_ok else "degraded",
        database="ok" if db_ok else "unreachable",
    )
