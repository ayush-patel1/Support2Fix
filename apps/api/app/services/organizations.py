"""Organization settings and member management. See security.md §4/§11:

every method takes an `organization_id` explicitly and never trusts a
caller-supplied one without the OrgContext dependency having verified
membership first (see app/api/deps.py) — that check happens in the route
layer, before these methods run.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AlreadyExistsError, ConflictError, NotFoundError
from app.models.membership import Membership, Role
from app.models.organization import Organization
from app.repositories.memberships import MembershipRepository
from app.repositories.organizations import OrganizationRepository
from app.repositories.users import UserRepository


class OrganizationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.organizations = OrganizationRepository(db)
        self.memberships = MembershipRepository(db)
        self.users = UserRepository(db)

    async def get(self, organization_id: uuid.UUID) -> Organization:
        org = await self.organizations.get_by_id(organization_id)
        if org is None:
            raise NotFoundError("Organization not found.")
        return org

    async def update(self, organization_id: uuid.UUID, *, name: str) -> Organization:
        org = await self.get(organization_id)
        updated = await self.organizations.update(org, name=name)
        await self.db.commit()
        return updated

    async def list_members(self, organization_id: uuid.UUID) -> list[tuple[Membership, str]]:
        """Returns (membership, email) pairs — routes shouldn't have to join

        against the users table themselves.
        """
        memberships = await self.memberships.list_for_organization(organization_id)
        results = []
        for m in memberships:
            user = await self.users.get_by_id(m.user_id)
            assert user is not None  # FK guarantees this
            results.append((m, user.email))
        return results

    async def add_member(self, organization_id: uuid.UUID, *, email: str, role: Role) -> Membership:
        user = await self.users.get_by_email(email)
        if user is None:
            raise NotFoundError(
                "No account with that email exists yet — they need to register first."
            )
        if await self.memberships.get(user.id, organization_id) is not None:
            raise AlreadyExistsError("That user is already a member of this organization.")

        membership = await self.memberships.create(
            user_id=user.id, organization_id=organization_id, role=role
        )
        await self.db.commit()
        return membership

    async def update_member_role(
        self, organization_id: uuid.UUID, *, user_id: uuid.UUID, role: Role
    ) -> Membership:
        membership = await self._get_membership_or_404(organization_id, user_id)
        if membership.role == Role.ADMIN and role != Role.ADMIN:
            await self._require_not_last_admin(organization_id)
        membership.role = role
        await self.db.flush()
        await self.db.commit()
        return membership

    async def remove_member(self, organization_id: uuid.UUID, *, user_id: uuid.UUID) -> None:
        membership = await self._get_membership_or_404(organization_id, user_id)
        if membership.role == Role.ADMIN:
            await self._require_not_last_admin(organization_id)
        await self.memberships.delete(membership)
        await self.db.commit()

    async def _get_membership_or_404(
        self, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> Membership:
        membership = await self.memberships.get(user_id, organization_id)
        if membership is None:
            raise NotFoundError("That user is not a member of this organization.")
        return membership

    async def _require_not_last_admin(self, organization_id: uuid.UUID) -> None:
        if await self.memberships.count_admins(organization_id) <= 1:
            raise ConflictError("Cannot remove or demote the last admin of an organization.")
