"""Data access for tickets and their timeline."""

import base64
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket, TicketEvent, TicketPriority, TicketStatus


@dataclass(frozen=True)
class TicketPage:
    items: list[Ticket]
    next_cursor: str | None


def _encode_cursor(created_at: datetime, ticket_id: uuid.UUID) -> str:
    raw = f"{created_at.isoformat()}|{ticket_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    created_at_str, id_str = raw.split("|", 1)
    return datetime.fromisoformat(created_at_str), uuid.UUID(id_str)


class TicketRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, organization_id: uuid.UUID, ticket_id: uuid.UUID) -> Ticket | None:
        stmt = select(Ticket).where(
            Ticket.id == ticket_id, Ticket.organization_id == organization_id
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list(
        self,
        organization_id: uuid.UUID,
        *,
        status: TicketStatus | None = None,
        priority: TicketPriority | None = None,
        customer_id: uuid.UUID | None = None,
        search: str | None = None,
        cursor: str | None = None,
        limit: int = 25,
    ) -> TicketPage:
        stmt = select(Ticket).where(Ticket.organization_id == organization_id)

        if status is not None:
            stmt = stmt.where(Ticket.status == status)
        if priority is not None:
            stmt = stmt.where(Ticket.priority == priority)
        if customer_id is not None:
            stmt = stmt.where(Ticket.customer_id == customer_id)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(or_(Ticket.title.ilike(like), Ticket.description.ilike(like)))
        if cursor:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    Ticket.created_at < cursor_created_at,
                    (Ticket.created_at == cursor_created_at) & (Ticket.id < cursor_id),
                )
            )

        stmt = stmt.order_by(Ticket.created_at.desc(), Ticket.id.desc()).limit(limit + 1)
        rows = list((await self.db.execute(stmt)).scalars().all())

        next_cursor = None
        if len(rows) > limit:
            rows = rows[:limit]
            last = rows[-1]
            next_cursor = _encode_cursor(last.created_at, last.id)

        return TicketPage(items=rows, next_cursor=next_cursor)

    async def create(self, **fields: object) -> Ticket:
        ticket = Ticket(**fields)
        self.db.add(ticket)
        await self.db.flush()
        return ticket

    async def update(self, ticket: Ticket, **fields: object) -> Ticket:
        for key, value in fields.items():
            setattr(ticket, key, value)
        await self.db.flush()
        return ticket


class TicketEventRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_ticket(
        self, organization_id: uuid.UUID, ticket_id: uuid.UUID
    ) -> list[TicketEvent]:
        stmt = (
            select(TicketEvent)
            .where(
                TicketEvent.ticket_id == ticket_id, TicketEvent.organization_id == organization_id
            )
            .order_by(TicketEvent.created_at.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def create(self, **fields: object) -> TicketEvent:
        event = TicketEvent(**fields)
        self.db.add(event)
        await self.db.flush()
        return event
