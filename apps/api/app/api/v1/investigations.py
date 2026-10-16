"""Authenticated investigation start, status, evidence, and timeline APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, get_org_context, require_role
from app.core.db import get_db
from app.models.investigation import InvestigationEvent
from app.models.membership import Role
from app.schemas.investigation import (
    InvestigationDetail,
    InvestigationEventPublic,
    InvestigationPublic,
)
from app.services.investigations import InvestigationService

router = APIRouter(tags=["investigations"])


@router.post(
    "/tickets/{ticket_id}/investigations",
    response_model=InvestigationPublic,
    status_code=202,
)
async def start_investigation(
    ticket_id: UUID,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=128),
    ctx: OrgContext = Depends(require_role(Role.SUPPORT)),
    db: AsyncSession = Depends(get_db),
) -> InvestigationPublic:
    investigation = await InvestigationService(db).start(
        ctx.organization_id,
        ticket_id,
        ctx.user_id,
        idempotency_key=idempotency_key,
    )
    return InvestigationPublic.model_validate(investigation)


@router.get("/investigations/{investigation_id}", response_model=InvestigationDetail)
async def get_investigation(
    investigation_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> InvestigationDetail:
    return await InvestigationService(db).get_detail(ctx.organization_id, investigation_id)


@router.get(
    "/investigations/{investigation_id}/events",
    response_model=list[InvestigationEventPublic],
)
async def list_investigation_events(
    investigation_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[InvestigationEventPublic]:
    events: list[InvestigationEvent] = await InvestigationService(db).list_events(
        ctx.organization_id, investigation_id
    )
    return [InvestigationEventPublic.model_validate(event) for event in events]
