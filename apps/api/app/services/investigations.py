"""Investigation lifecycle, including atomic ticket transition and queueing."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.investigation import (
    Investigation,
    InvestigationEvent,
    InvestigationEventType,
    InvestigationStatus,
)
from app.models.ticket import Ticket, TicketEvent, TicketEventType, TicketStatus
from app.models.tool_call import Evidence, ToolCall
from app.repositories.investigations import InvestigationRepository
from app.schemas.investigation import (
    EvidencePublic,
    InvestigationDetail,
    InvestigationPublic,
    InvestigationTimelineItem,
)
from app.services.tickets import ALLOWED_TRANSITIONS


def build_investigation_timeline(
    events: Sequence[InvestigationEvent],
    evidence: Sequence[EvidencePublic],
) -> list[InvestigationTimelineItem]:
    timeline = [
        InvestigationTimelineItem(
            id=event.id,
            kind="EVENT",
            occurred_at=event.created_at,
            title=event.message,
            details=event.details,
        )
        for event in events
    ]
    timeline.extend(
        InvestigationTimelineItem(
            id=item.id,
            kind="EVIDENCE",
            occurred_at=item.observed_at,
            title=f"Collected {item.kind} evidence with {item.tool_name}.",
            details={"source_ref": item.source_ref, "content_sha256": item.content_sha256},
            evidence_id=item.id,
        )
        for item in evidence
    )
    timeline.sort(key=lambda item: (item.occurred_at, str(item.id)))
    return timeline


class InvestigationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.investigations = InvestigationRepository(db)

    async def start(
        self,
        organization_id: uuid.UUID,
        ticket_id: uuid.UUID,
        actor_id: uuid.UUID,
        *,
        idempotency_key: str | None = None,
    ) -> Investigation:
        if idempotency_key:
            existing_stmt = select(Investigation).where(
                Investigation.organization_id == organization_id,
                Investigation.idempotency_key == idempotency_key,
            )
            existing = (await self.db.execute(existing_stmt)).scalar_one_or_none()
            if existing is not None:
                if existing.ticket_id != ticket_id:
                    raise ConflictError("Idempotency-Key was already used for another ticket.")
                return existing

        ticket_stmt = (
            select(Ticket)
            .where(Ticket.id == ticket_id, Ticket.organization_id == organization_id)
            .with_for_update()
        )
        ticket = (await self.db.execute(ticket_stmt)).scalar_one_or_none()
        if ticket is None:
            raise NotFoundError("Ticket not found.")

        active = await self.investigations.active_for_ticket(organization_id, ticket_id)
        if active is not None:
            raise ConflictError("This ticket already has an active investigation.")

        if ticket.status not in {TicketStatus.OPEN, TicketStatus.ESCALATED}:
            raise ConflictError(
                f"Cannot investigate a ticket in {ticket.status.value} status."
            )
        if TicketStatus.INVESTIGATING not in ALLOWED_TRANSITIONS[ticket.status]:
            raise ConflictError(f"Ticket status {ticket.status.value} cannot be investigated.")

        previous_status = ticket.status
        investigation = await self.investigations.create(
            organization_id=organization_id,
            ticket_id=ticket.id,
            started_by=actor_id,
            status=InvestigationStatus.QUEUED,
            idempotency_key=idempotency_key,
        )
        await self.investigations.add_event(
            organization_id=organization_id,
            investigation_id=investigation.id,
            type=InvestigationEventType.QUEUED,
            message="Investigation queued for evidence collection.",
        )
        await self.investigations.create_job(
            organization_id=organization_id,
            investigation_id=investigation.id,
        )

        ticket.status = TicketStatus.INVESTIGATING
        self.db.add(
            TicketEvent(
                organization_id=organization_id,
                ticket_id=ticket.id,
                actor_user_id=actor_id,
                type=TicketEventType.STATUS_CHANGED,
                payload={"from": previous_status.value, "to": TicketStatus.INVESTIGATING.value},
            )
        )
        await self.db.commit()
        await self.db.refresh(investigation)
        return investigation

    async def get_detail(
        self, organization_id: uuid.UUID, investigation_id: uuid.UUID
    ) -> InvestigationDetail:
        investigation = await self.investigations.get(organization_id, investigation_id)
        if investigation is None:
            raise NotFoundError("Investigation not found.")

        evidence_stmt = (
            select(Evidence, ToolCall.tool_name)
            .join(
                ToolCall,
                (ToolCall.id == Evidence.tool_call_id)
                & (ToolCall.organization_id == Evidence.organization_id),
            )
            .where(
                Evidence.organization_id == organization_id,
                Evidence.investigation_id == investigation_id,
            )
            .order_by(Evidence.observed_at, Evidence.id)
            .limit(100)
        )
        rows = (await self.db.execute(evidence_stmt)).all()
        evidence = [
            EvidencePublic(
                id=item.id,
                kind=item.kind,
                source_ref=item.source_ref,
                content=item.content,
                content_sha256=item.content_sha256,
                observed_at=item.observed_at,
                tool_name=tool_name,
            )
            for item, tool_name in rows
        ]
        events = await self.investigations.list_events(organization_id, investigation_id)
        return InvestigationDetail(
            **InvestigationPublic.model_validate(investigation).model_dump(),
            evidence=evidence,
            timeline=build_investigation_timeline(events, evidence),
        )

    async def list_events(
        self, organization_id: uuid.UUID, investigation_id: uuid.UUID
    ) -> list[InvestigationEvent]:
        if await self.investigations.get(organization_id, investigation_id) is None:
            raise NotFoundError("Investigation not found.")
        return await self.investigations.list_events(organization_id, investigation_id)
