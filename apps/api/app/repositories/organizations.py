import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.slug import candidate_slugs
from app.models.organization import Organization


class OrganizationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, organization_id: uuid.UUID) -> Organization | None:
        return await self.db.get(Organization, organization_id)

    async def create(self, *, name: str) -> Organization:
        """Tries slugified variants of `name` until one doesn't collide with

        an existing organization's slug (see core/slug.py).
        """
        last_error: IntegrityError | None = None
        for slug in candidate_slugs(name):
            org = Organization(name=name, slug=slug)
            self.db.add(org)
            try:
                await self.db.flush()
                return org
            except IntegrityError as exc:
                await self.db.rollback()
                last_error = exc
        assert last_error is not None
        raise last_error

    async def update(self, org: Organization, *, name: str) -> Organization:
        org.name = name
        await self.db.flush()
        return org
