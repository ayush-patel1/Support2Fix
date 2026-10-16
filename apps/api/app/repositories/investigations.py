"""Tenant-scoped persistence for investigation records and queue jobs."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investigation import (
    Investigation,
    InvestigationEvent,
    InvestigationJob,
    InvestigationStatus,
)


class InvestigationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(
        self, organization_id: uuid.UUID, investigation_id: uuid.UUID
    ) -> Investigation | None:
        stmt = select(Investigation).where(
            Investigation.organization_id == organization_id,
            Investigation.id == investigation_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def active_for_ticket(
        self, organization_id: uuid.UUID, ticket_id: uuid.UUID
    ) -> Investigation | None:
        stmt = select(Investigation).where(
            Investigation.organization_id == organization_id,
            Investigation.ticket_id == ticket_id,
            Investigation.status.in_(
                [InvestigationStatus.QUEUED, InvestigationStatus.RUNNING]
            ),
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create(self, **fields: object) -> Investigation:
        investigation = Investigation(**fields)
        self.db.add(investigation)
        await self.db.flush()
        return investigation

    async def add_event(self, **fields: object) -> InvestigationEvent:
        event = InvestigationEvent(**fields)
        self.db.add(event)
        await self.db.flush()
        return event

    async def list_events(
        self, organization_id: uuid.UUID, investigation_id: uuid.UUID
    ) -> list[InvestigationEvent]:
        stmt = (
            select(InvestigationEvent)
            .where(
                InvestigationEvent.organization_id == organization_id,
                InvestigationEvent.investigation_id == investigation_id,
            )
            .order_by(InvestigationEvent.created_at, InvestigationEvent.id)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def create_job(self, **fields: object) -> InvestigationJob:
        job = InvestigationJob(**fields)
        self.db.add(job)
        await self.db.flush()
        return job
