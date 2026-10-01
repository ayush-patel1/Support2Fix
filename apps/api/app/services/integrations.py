"""Integration CRUD plus the test-connection check. See

app/integrations/registry.py for how an Integration record becomes a
concrete adapter, and app/integrations/base.py for the five interfaces.

Config is validated eagerly on create/update by actually attempting to
build the adapter (`registry.build_adapter`) — one source of truth for
"what does this (kind, provider) need," instead of a second, separately
maintained list of required keys that could drift from the factory.
"""

import uuid
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidConfigError, NotFoundError
from app.integrations.base import CodeHost, DataSource, DeploymentSource, LogSource
from app.integrations.registry import build_adapter
from app.models.integration import Integration, IntegrationKind, IntegrationProvider
from app.repositories.integrations import IntegrationRepository
from app.schemas.integration import IntegrationTestResult


class IntegrationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.integrations = IntegrationRepository(db)

    def _validate_config(self, integration: Integration) -> None:
        if integration.kind == IntegrationKind.SUPPORT_SOURCE:
            return  # needs a live db session to build; nothing to validate up front
        try:
            build_adapter(integration)
        except ValueError as exc:
            raise InvalidConfigError(str(exc)) from exc

    async def create_integration(
        self,
        organization_id: uuid.UUID,
        *,
        kind: IntegrationKind,
        provider: IntegrationProvider,
        name: str,
        config: dict[str, object],
    ) -> Integration:
        integration = Integration(
            organization_id=organization_id,
            kind=kind,
            provider=provider,
            name=name,
            config=config,
        )
        self._validate_config(integration)
        integration = await self.integrations.create(
            organization_id=organization_id, kind=kind, provider=provider, name=name, config=config
        )
        await self.db.commit()
        return integration

    async def get_integration(
        self, organization_id: uuid.UUID, integration_id: uuid.UUID
    ) -> Integration:
        integration = await self.integrations.get(organization_id, integration_id)
        if integration is None:
            raise NotFoundError("Integration not found.")
        return integration

    async def list_integrations(
        self, organization_id: uuid.UUID, *, kind: IntegrationKind | None = None
    ) -> list[Integration]:
        return await self.integrations.list(organization_id, kind=kind)

    async def update_integration(
        self,
        organization_id: uuid.UUID,
        integration_id: uuid.UUID,
        *,
        name: str | None = None,
        config: dict[str, object] | None = None,
    ) -> Integration:
        integration = await self.get_integration(organization_id, integration_id)
        if config is not None:
            candidate = Integration(
                organization_id=integration.organization_id,
                kind=integration.kind,
                provider=integration.provider,
                name=name or integration.name,
                config=config,
            )
            self._validate_config(candidate)
        fields = {k: v for k, v in {"name": name, "config": config}.items() if v is not None}
        integration = await self.integrations.update(integration, **fields)
        await self.db.commit()
        return integration

    async def delete_integration(
        self, organization_id: uuid.UUID, integration_id: uuid.UUID
    ) -> None:
        integration = await self.get_integration(organization_id, integration_id)
        await self.integrations.delete(integration)
        await self.db.commit()

    async def test_connection(
        self, organization_id: uuid.UUID, integration_id: uuid.UUID
    ) -> IntegrationTestResult:
        integration = await self.get_integration(organization_id, integration_id)
        try:
            adapter = build_adapter(integration, db=self.db)
            if integration.kind == IntegrationKind.CODE_HOST:
                await cast(CodeHost, adapter).list_commits(limit=1)
            elif integration.kind == IntegrationKind.LOG_SOURCE:
                await cast(LogSource, adapter).search("", limit=1)
            elif integration.kind == IntegrationKind.DATA_SOURCE:
                await cast(DataSource, adapter).get_schema()
            elif integration.kind == IntegrationKind.DEPLOYMENT_SOURCE:
                await cast(DeploymentSource, adapter).list_releases(limit=1)
            # SUPPORT_SOURCE wraps this same database — nothing external to reach.
        except Exception as exc:  # reporting the failure *is* the feature — never propagate
            return IntegrationTestResult(ok=False, detail=f"{type(exc).__name__}: {exc}")
        return IntegrationTestResult(ok=True, detail="Connection succeeded.")
