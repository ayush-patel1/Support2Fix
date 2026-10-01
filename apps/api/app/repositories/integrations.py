"""Data access for Integration records. Same tenant-scoping discipline as

app/repositories/customers.py: every method takes `organization_id`
explicitly and filters on it.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import Integration, IntegrationKind


class IntegrationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(
        self, organization_id: uuid.UUID, integration_id: uuid.UUID
    ) -> Integration | None:
        stmt = select(Integration).where(
            Integration.id == integration_id, Integration.organization_id == organization_id
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list(
        self, organization_id: uuid.UUID, *, kind: IntegrationKind | None = None
    ) -> list[Integration]:
        stmt = select(Integration).where(Integration.organization_id == organization_id)
        if kind is not None:
            stmt = stmt.where(Integration.kind == kind)
        stmt = stmt.order_by(Integration.name)
        return list((await self.db.execute(stmt)).scalars().all())

    async def create(self, **fields: object) -> Integration:
        integration = Integration(**fields)
        self.db.add(integration)
        await self.db.flush()
        return integration

    async def update(self, integration: Integration, **fields: object) -> Integration:
        for key, value in fields.items():
            setattr(integration, key, value)
        await self.db.flush()
        return integration

    async def delete(self, integration: Integration) -> None:
        await self.db.delete(integration)
        await self.db.flush()
