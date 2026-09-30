"""Organization + member management, all scoped to the caller's *active*

organization (from their session — see app/api/deps.py). There is no
route that takes an arbitrary organization id from the client: that's what
makes cross-tenant access structurally impossible here, rather than just
checked. See system-design.md §7.1 and security.md §11.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, get_org_context, require_role
from app.core.db import get_db
from app.models.membership import Role
from app.schemas.organization import (
    AddMemberRequest,
    MemberPublic,
    OrganizationPublic,
    OrganizationUpdate,
    UpdateMemberRoleRequest,
)
from app.services.organizations import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/current", response_model=OrganizationPublic)
async def get_current_organization(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> OrganizationPublic:
    org = await OrganizationService(db).get(ctx.organization_id)
    return OrganizationPublic.model_validate(org)


@router.patch("/current", response_model=OrganizationPublic)
async def update_current_organization(
    body: OrganizationUpdate,
    ctx: OrgContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> OrganizationPublic:
    org = await OrganizationService(db).update(ctx.organization_id, name=body.name)
    return OrganizationPublic.model_validate(org)


@router.get("/current/members", response_model=list[MemberPublic])
async def list_members(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[MemberPublic]:
    pairs = await OrganizationService(db).list_members(ctx.organization_id)
    return [MemberPublic(user_id=m.user_id, email=email, role=m.role) for m, email in pairs]


@router.post("/current/members", response_model=MemberPublic, status_code=201)
async def add_member(
    body: AddMemberRequest,
    ctx: OrgContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> MemberPublic:
    membership = await OrganizationService(db).add_member(
        ctx.organization_id, email=body.email, role=body.role
    )
    return MemberPublic(user_id=membership.user_id, email=body.email, role=membership.role)


@router.patch("/current/members/{user_id}", response_model=MemberPublic)
async def update_member_role(
    user_id: UUID,
    body: UpdateMemberRoleRequest,
    ctx: OrgContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> MemberPublic:
    service = OrganizationService(db)
    membership = await service.update_member_role(
        ctx.organization_id, user_id=user_id, role=body.role
    )
    pairs = await service.list_members(ctx.organization_id)
    email = next(email for m, email in pairs if m.user_id == user_id)
    return MemberPublic(user_id=membership.user_id, email=email, role=membership.role)


@router.delete("/current/members/{user_id}", status_code=204)
async def remove_member(
    user_id: UUID,
    ctx: OrgContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> None:
    await OrganizationService(db).remove_member(ctx.organization_id, user_id=user_id)
