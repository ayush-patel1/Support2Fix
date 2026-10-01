"""Integration configuration routes. Restricted to ADMIN — these adapters

reach into an organization's own repos, logs, and databases, so who can
configure them is tighter than who can read tickets/customers (see
system-design.md §7.2's API table: "configure, test connection ...
ADMIN").
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, require_role
from app.core.db import get_db
from app.models.integration import IntegrationKind
from app.models.membership import Role
from app.schemas.integration import (
    IntegrationCreate,
    IntegrationPublic,
    IntegrationTestResult,
    IntegrationUpdate,
)
from app.services.integrations import IntegrationService

router = APIRouter(tags=["integrations"])


@router.post("/integrations", response_model=IntegrationPublic, status_code=201)
async def create_integration(
    body: IntegrationCreate,
    ctx: OrgContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> IntegrationPublic:
    integration = await IntegrationService(db).create_integration(
        ctx.organization_id,
        kind=body.kind,
        provider=body.provider,
        name=body.name,
        config=body.config,
    )
    return IntegrationPublic.model_validate(integration)


@router.get("/integrations", response_model=list[IntegrationPublic])
async def list_integrations(
    kind: IntegrationKind | None = None,
    ctx: OrgContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[IntegrationPublic]:
    integrations = await IntegrationService(db).list_integrations(ctx.organization_id, kind=kind)
    return [IntegrationPublic.model_validate(i) for i in integrations]


@router.get("/integrations/{integration_id}", response_model=IntegrationPublic)
async def get_integration(
    integration_id: UUID,
    ctx: OrgContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> IntegrationPublic:
    integration = await IntegrationService(db).get_integration(ctx.organization_id, integration_id)
    return IntegrationPublic.model_validate(integration)


@router.patch("/integrations/{integration_id}", response_model=IntegrationPublic)
async def update_integration(
    integration_id: UUID,
    body: IntegrationUpdate,
    ctx: OrgContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> IntegrationPublic:
    integration = await IntegrationService(db).update_integration(
        ctx.organization_id, integration_id, name=body.name, config=body.config
    )
    return IntegrationPublic.model_validate(integration)


@router.delete("/integrations/{integration_id}", status_code=204)
async def delete_integration(
    integration_id: UUID,
    ctx: OrgContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> None:
    await IntegrationService(db).delete_integration(ctx.organization_id, integration_id)


@router.post("/integrations/{integration_id}/test", response_model=IntegrationTestResult)
async def test_integration(
    integration_id: UUID,
    ctx: OrgContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> IntegrationTestResult:
    return await IntegrationService(db).test_connection(ctx.organization_id, integration_id)
