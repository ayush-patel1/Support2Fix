"""Ticket routes: create, edit, filter/search, status transitions, and the

timeline. See system-design.md §7.2 and Phase 3.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, get_org_context, require_role
from app.core.db import get_db
from app.models.membership import Role
from app.models.ticket import TicketPriority, TicketStatus
from app.schemas.ticket import (
    TicketCommentCreate,
    TicketCreate,
    TicketEventPublic,
    TicketListResponse,
    TicketPublic,
    TicketStatusUpdate,
    TicketUpdate,
)
from app.services.tickets import TicketService

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketPublic, status_code=201)
async def create_ticket(
    body: TicketCreate,
    ctx: OrgContext = Depends(require_role(Role.SUPPORT)),
    db: AsyncSession = Depends(get_db),
) -> TicketPublic:
    ticket = await TicketService(db).create_ticket(
        ctx.organization_id,
        customer_id=body.customer_id,
        created_by=ctx.user_id,
        title=body.title,
        description=body.description,
        priority=body.priority,
    )
    return TicketPublic.model_validate(ticket)


@router.get("", response_model=TicketListResponse)
async def list_tickets(
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
    customer_id: UUID | None = None,
    search: str | None = Query(default=None, max_length=200),
    cursor: str | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> TicketListResponse:
    page = await TicketService(db).list_tickets(
        ctx.organization_id,
        status=status,
        priority=priority,
        customer_id=customer_id,
        search=search,
        cursor=cursor,
        limit=limit,
    )
    return TicketListResponse(
        items=[TicketPublic.model_validate(t) for t in page.items], next_cursor=page.next_cursor
    )


@router.get("/{ticket_id}", response_model=TicketPublic)
async def get_ticket(
    ticket_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> TicketPublic:
    ticket = await TicketService(db).get_ticket(ctx.organization_id, ticket_id)
    return TicketPublic.model_validate(ticket)


@router.patch("/{ticket_id}", response_model=TicketPublic)
async def update_ticket(
    ticket_id: UUID,
    body: TicketUpdate,
    ctx: OrgContext = Depends(require_role(Role.SUPPORT)),
    db: AsyncSession = Depends(get_db),
) -> TicketPublic:
    ticket = await TicketService(db).update_ticket(
        ctx.organization_id,
        ticket_id,
        ctx.user_id,
        title=body.title,
        description=body.description,
        priority=body.priority,
    )
    return TicketPublic.model_validate(ticket)


@router.post("/{ticket_id}/status", response_model=TicketPublic)
async def change_ticket_status(
    ticket_id: UUID,
    body: TicketStatusUpdate,
    ctx: OrgContext = Depends(require_role(Role.SUPPORT)),
    db: AsyncSession = Depends(get_db),
) -> TicketPublic:
    ticket = await TicketService(db).change_status(
        ctx.organization_id, ticket_id, ctx.user_id, new_status=body.status
    )
    return TicketPublic.model_validate(ticket)


@router.get("/{ticket_id}/events", response_model=list[TicketEventPublic])
async def list_ticket_events(
    ticket_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[TicketEventPublic]:
    events = await TicketService(db).list_events(ctx.organization_id, ticket_id)
    return [TicketEventPublic.model_validate(e) for e in events]


@router.post("/{ticket_id}/events", response_model=TicketEventPublic, status_code=201)
async def add_ticket_comment(
    ticket_id: UUID,
    body: TicketCommentCreate,
    ctx: OrgContext = Depends(require_role(Role.SUPPORT)),
    db: AsyncSession = Depends(get_db),
) -> TicketEventPublic:
    event = await TicketService(db).add_comment(
        ctx.organization_id, ticket_id, ctx.user_id, comment=body.comment
    )
    return TicketEventPublic.model_validate(event)
