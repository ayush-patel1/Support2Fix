"""Database-backed investigation queue consumer.

Run with `python -m app.worker.main`.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import httpx2
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.db import dispose_engine, get_engine, init_engine
from app.mcp.gateway import ToolGateway
from app.models.investigation import (
    Investigation,
    InvestigationEvent,
    InvestigationEventType,
    InvestigationJob,
    InvestigationStatus,
)
from app.models.ticket import Ticket, TicketEvent, TicketEventType, TicketStatus
from app.worker.investigations import collect_investigation

logger = logging.getLogger("support2fix.worker")
MAX_ATTEMPTS = 3
LEASE_SECONDS = 180


@asynccontextmanager
async def _connected_gateway(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[ToolGateway]:
    settings = get_settings()
    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {settings.mcp_service_token}"},
        timeout=30,
    ) as http_client:
        async with streamable_http_client(
            settings.mcp_server_url, http_client=http_client
        ) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as client:
                await client.initialize()
                yield ToolGateway(client, session_factory)


async def _claim_job(
    session_factory: async_sessionmaker[AsyncSession], worker_id: str
) -> uuid.UUID | None:
    now = datetime.now(UTC)
    async with session_factory() as db:
        statement = (
            select(InvestigationJob)
            .where(
                InvestigationJob.status.in_(["QUEUED", "RUNNING"]),
                InvestigationJob.run_after <= now,
                or_(
                    InvestigationJob.locked_until.is_(None),
                    InvestigationJob.locked_until < now,
                ),
            )
            .order_by(InvestigationJob.run_after, InvestigationJob.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        job = (await db.execute(statement)).scalar_one_or_none()
        if job is None:
            return None
        job.status = "RUNNING"
        job.attempts += 1
        job.locked_by = worker_id
        job.locked_until = now + timedelta(seconds=LEASE_SECONDS)
        await db.commit()
        return job.investigation_id


async def _record_failure(
    session_factory: async_sessionmaker[AsyncSession],
    investigation_id: uuid.UUID,
    worker_id: str,
    error: Exception,
) -> None:
    now = datetime.now(UTC)
    async with session_factory() as db:
        job = (
            await db.execute(
                select(InvestigationJob)
                .where(InvestigationJob.investigation_id == investigation_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        investigation = await db.get(Investigation, investigation_id)
        if job is None or investigation is None or job.locked_by != worker_id:
            return

        job.last_error = f"{type(error).__name__}: {error}"[:1000]
        job.locked_by = None
        job.locked_until = None
        if job.attempts < MAX_ATTEMPTS:
            job.status = "QUEUED"
            job.run_after = now + timedelta(seconds=5 * (2 ** (job.attempts - 1)))
            investigation.status = InvestigationStatus.QUEUED
            db.add(
                InvestigationEvent(
                    organization_id=investigation.organization_id,
                    investigation_id=investigation.id,
                    type=InvestigationEventType.QUEUED,
                    message="A transient worker failure occurred; retry scheduled.",
                    details={"attempt": job.attempts, "error_type": type(error).__name__},
                )
            )
        else:
            job.status = "FAILED"
            investigation.status = InvestigationStatus.FAILED
            investigation.summary = (
                "Evidence collection failed after the maximum number of worker attempts."
            )
            investigation.evidence_gaps = [job.last_error]
            investigation.completed_at = now
            db.add(
                InvestigationEvent(
                    organization_id=investigation.organization_id,
                    investigation_id=investigation.id,
                    type=InvestigationEventType.FAILED,
                    message=investigation.summary,
                    details={"attempts": job.attempts},
                )
            )
            ticket = (
                await db.execute(
                    select(Ticket)
                    .where(
                        Ticket.id == investigation.ticket_id,
                        Ticket.organization_id == investigation.organization_id,
                    )
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if ticket is not None and ticket.status == TicketStatus.INVESTIGATING:
                ticket.status = TicketStatus.ESCALATED
                db.add(
                    TicketEvent(
                        organization_id=ticket.organization_id,
                        ticket_id=ticket.id,
                        actor_user_id=None,
                        type=TicketEventType.STATUS_CHANGED,
                        payload={
                            "from": TicketStatus.INVESTIGATING.value,
                            "to": TicketStatus.ESCALATED.value,
                        },
                    )
                )
        await db.commit()


async def run_worker() -> None:
    settings = get_settings()
    init_engine(settings.database_url, echo=settings.database_echo)
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    worker_id = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4()}"
    logger.info("Investigation worker started", extra={"worker_id": worker_id})
    try:
        while True:
            investigation_id = await _claim_job(session_factory, worker_id)
            if investigation_id is None:
                await asyncio.sleep(settings.worker_poll_seconds)
                continue
            try:
                async with _connected_gateway(session_factory) as gateway:
                    await collect_investigation(investigation_id, session_factory, gateway)
            except Exception as exc:
                logger.exception(
                    "Investigation job failed",
                    extra={"investigation_id": str(investigation_id), "worker_id": worker_id},
                )
                await _record_failure(session_factory, investigation_id, worker_id, exc)
    finally:
        await dispose_engine()


if __name__ == "__main__":
    logging.basicConfig(level=get_settings().log_level)
    asyncio.run(run_worker())
