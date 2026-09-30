import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.membership import Membership, Role


class MembershipRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> Membership | None:
        stmt = select(Membership).where(
            Membership.user_id == user_id, Membership.organization_id == organization_id
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> list[Membership]:
        stmt = (
            select(Membership).where(Membership.user_id == user_id).order_by(Membership.created_at)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_for_organization(self, organization_id: uuid.UUID) -> list[Membership]:
        stmt = select(Membership).where(Membership.organization_id == organization_id)
        return list((await self.db.execute(stmt)).scalars().all())

    async def count_admins(self, organization_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            Membership.organization_id == organization_id, Membership.role == Role.ADMIN
        )
        return (await self.db.execute(stmt)).scalar_one()

    async def create(
        self, *, user_id: uuid.UUID, organization_id: uuid.UUID, role: Role
    ) -> Membership:
        membership = Membership(user_id=user_id, organization_id=organization_id, role=role)
        self.db.add(membership)
        await self.db.flush()
        return membership

    async def delete(self, membership: Membership) -> None:
        await self.db.delete(membership)
        await self.db.flush()
