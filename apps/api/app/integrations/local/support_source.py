"""SupportSource backed by Support2Fix's own ticket system — no external

helpdesk vendor. `base.py` notes `SupportSource` is only needed when an
*external* support tool feeds issues in; this adapter is the trivial case
where the "external" tool is the platform's own Phase 3/4 data, exposed
through the same interface an agent would use for, say, a Zendesk adapter.

Scoped to one organization at construction time — unlike `CodeHost` or
`LogSource`, ticket/customer records are already tenant-isolated by
`organization_id` (system-design.md §6), so an instance of this adapter is
only ever valid for the single organization its owning `Integration`
record belongs to.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.customer import CustomerPublic
from app.schemas.ticket import TicketPublic
from app.services.customers import CustomerService
from app.services.tickets import TicketService


class LocalTicketSupportSource:
    def __init__(self, db: AsyncSession, organization_id: uuid.UUID) -> None:
        self.organization_id = organization_id
        self.tickets = TicketService(db)
        self.customers = CustomerService(db)

    async def get_ticket(self, ticket_id: str) -> dict[str, Any]:
        ticket = await self.tickets.get_ticket(self.organization_id, uuid.UUID(ticket_id))
        return TicketPublic.model_validate(ticket).model_dump(mode="json")

    async def get_customer(self, customer_id: str) -> dict[str, Any]:
        customer = await self.customers.get_customer(self.organization_id, uuid.UUID(customer_id))
        return CustomerPublic.model_validate(customer).model_dump(mode="json")
