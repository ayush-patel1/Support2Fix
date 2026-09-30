"""Ticket CRUD, filtering/search, and the status state machine from

system-design.md §5.2. This is the one place status is allowed to change —
every transition is checked against ALLOWED_TRANSITIONS and recorded as a
timeline event, whether a human changes it now or the (future) agent does
later; the rule doesn't change based on who's asking.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.ticket import Ticket, TicketEvent, TicketEventType, TicketPriority, TicketStatus
from app.repositories.customers import CustomerRepository
from app.repositories.tickets import TicketEventRepository, TicketPage, TicketRepository

# See system-design.md §5.2 for the state diagram this encodes. RESOLVED
# has no outgoing edges — it's terminal, matching the diagram's `[*]`.
ALLOWED_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.OPEN: {TicketStatus.INVESTIGATING},
    TicketStatus.INVESTIGATING: {TicketStatus.ROOT_CAUSE_FOUND, TicketStatus.ESCALATED},
    TicketStatus.ROOT_CAUSE_FOUND: {TicketStatus.FIX_PROPOSED},
    TicketStatus.FIX_PROPOSED: {TicketStatus.VALIDATING, TicketStatus.ESCALATED},
    TicketStatus.VALIDATING: {
        TicketStatus.FIX_PROPOSED,
        TicketStatus.INVESTIGATING,
        TicketStatus.RESOLVED,
    },
    TicketStatus.ESCALATED: {TicketStatus.INVESTIGATING},
    TicketStatus.RESOLVED: set(),
}


class TicketService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.tickets = TicketRepository(db)
        self.events = TicketEventRepository(db)
        self.customers = CustomerRepository(db)

    async def create_ticket(
        self,
        organization_id: uuid.UUID,
        *,
        customer_id: uuid.UUID,
        created_by: uuid.UUID,
        title: str,
        description: str,
        priority: TicketPriority,
    ) -> Ticket:
        if await self.customers.get(organization_id, customer_id) is None:
            raise NotFoundError("Customer not found.")

        ticket = await self.tickets.create(
            organization_id=organization_id,
            customer_id=customer_id,
            created_by=created_by,
            title=title,
            description=description,
            priority=priority,
        )
        await self.events.create(
            organization_id=organization_id,
            ticket_id=ticket.id,
            actor_user_id=created_by,
            type=TicketEventType.CREATED,
            payload={"title": title, "priority": priority.value},
        )
        await self.db.commit()
        return ticket

    async def get_ticket(self, organization_id: uuid.UUID, ticket_id: uuid.UUID) -> Ticket:
        ticket = await self.tickets.get(organization_id, ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket not found.")
        return ticket

    async def list_tickets(
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
        return await self.tickets.list(
            organization_id,
            status=status,
            priority=priority,
            customer_id=customer_id,
            search=search,
            cursor=cursor,
            limit=limit,
        )

    async def update_ticket(
        self,
        organization_id: uuid.UUID,
        ticket_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        *,
        title: str | None = None,
        description: str | None = None,
        priority: TicketPriority | None = None,
    ) -> Ticket:
        ticket = await self.get_ticket(organization_id, ticket_id)
        candidates = {"title": title, "description": description, "priority": priority}
        changes = {k: v for k, v in candidates.items() if v is not None and v != getattr(ticket, k)}

        if not changes:
            return ticket

        for field, new_value in changes.items():
            old_value = getattr(ticket, field)
            await self.events.create(
                organization_id=organization_id,
                ticket_id=ticket.id,
                actor_user_id=actor_user_id,
                type=TicketEventType.FIELD_CHANGED,
                payload={
                    "field": field,
                    "from": old_value.value if hasattr(old_value, "value") else old_value,
                    "to": new_value.value if hasattr(new_value, "value") else new_value,
                },
            )

        updated = await self.tickets.update(ticket, **changes)
        await self.db.commit()
        return updated

    async def change_status(
        self,
        organization_id: uuid.UUID,
        ticket_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        *,
        new_status: TicketStatus,
    ) -> Ticket:
        ticket = await self.get_ticket(organization_id, ticket_id)
        current = ticket.status

        if new_status == current:
            return ticket
        if new_status not in ALLOWED_TRANSITIONS.get(current, set()):
            allowed = (
                ", ".join(s.value for s in ALLOWED_TRANSITIONS.get(current, set()))
                or "(none — terminal)"
            )
            raise ConflictError(
                f"Cannot move a ticket from {current.value} to {new_status.value}. "
                f"Allowed from {current.value}: {allowed}."
            )

        await self.events.create(
            organization_id=organization_id,
            ticket_id=ticket.id,
            actor_user_id=actor_user_id,
            type=TicketEventType.STATUS_CHANGED,
            payload={"from": current.value, "to": new_status.value},
        )
        updated = await self.tickets.update(ticket, status=new_status)
        await self.db.commit()
        return updated

    async def add_comment(
        self,
        organization_id: uuid.UUID,
        ticket_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        *,
        comment: str,
    ) -> TicketEvent:
        await self.get_ticket(organization_id, ticket_id)  # 404s if missing
        event = await self.events.create(
            organization_id=organization_id,
            ticket_id=ticket_id,
            actor_user_id=actor_user_id,
            type=TicketEventType.COMMENT,
            payload={"comment": comment},
        )
        await self.db.commit()
        return event

    async def list_events(
        self, organization_id: uuid.UUID, ticket_id: uuid.UUID
    ) -> list[TicketEvent]:
        await self.get_ticket(organization_id, ticket_id)  # 404s if missing
        return await self.events.list_for_ticket(organization_id, ticket_id)
