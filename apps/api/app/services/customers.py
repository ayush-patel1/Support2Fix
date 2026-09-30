"""Customer context: create/list customers and their environment ->

service -> {repository, deployment} chain, and assemble the environment
overview view. See system-design.md §6 and Phase 4.

Every "create a child" method takes the claimed parent id and verifies it
actually belongs to this organization before inserting — the composite FK
would catch a *cross-org* mismatch at the database level regardless, but a
parent id that's simply wrong (or nonexistent) needs a clean 404, not a
raw constraint-violation error bubbling up.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.customer import (
    CodeRepository,
    Customer,
    CustomerEnvironment,
    CustomerTier,
    Deployment,
    DeploymentStatus,
    RepositoryProvider,
    Service,
)
from app.repositories.customers import (
    CodeRepositoryRepository,
    CustomerEnvironmentRepository,
    CustomerRepository,
    DeploymentRepository,
    ServiceRepository,
)


@dataclass(frozen=True)
class ServiceWithChildren:
    service: Service
    repositories: list[CodeRepository]
    deployments: list[Deployment]


@dataclass(frozen=True)
class EnvironmentOverview:
    environment: CustomerEnvironment
    services: list[ServiceWithChildren]


class CustomerService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.customers = CustomerRepository(db)
        self.environments = CustomerEnvironmentRepository(db)
        self.services = ServiceRepository(db)
        self.repositories = CodeRepositoryRepository(db)
        self.deployments = DeploymentRepository(db)

    # --- customers -----------------------------------------------------

    async def create_customer(
        self,
        organization_id: uuid.UUID,
        *,
        name: str,
        external_ref: str | None,
        tier: CustomerTier,
    ) -> Customer:
        customer = await self.customers.create(
            organization_id=organization_id, name=name, external_ref=external_ref, tier=tier
        )
        await self.db.commit()
        return customer

    async def get_customer(self, organization_id: uuid.UUID, customer_id: uuid.UUID) -> Customer:
        customer = await self.customers.get(organization_id, customer_id)
        if customer is None:
            raise NotFoundError("Customer not found.")
        return customer

    async def list_customers(self, organization_id: uuid.UUID) -> list[Customer]:
        return await self.customers.list(organization_id)

    async def update_customer(
        self,
        organization_id: uuid.UUID,
        customer_id: uuid.UUID,
        *,
        name: str | None = None,
        external_ref: str | None = None,
        tier: CustomerTier | None = None,
    ) -> Customer:
        customer = await self.get_customer(organization_id, customer_id)
        fields = {
            k: v
            for k, v in {"name": name, "external_ref": external_ref, "tier": tier}.items()
            if v is not None
        }
        updated = await self.customers.update(customer, **fields)
        await self.db.commit()
        return updated

    # --- environments ----------------------------------------------------

    async def create_environment(
        self, organization_id: uuid.UUID, customer_id: uuid.UUID, *, name: str
    ) -> CustomerEnvironment:
        await self.get_customer(organization_id, customer_id)  # 404s if wrong/missing
        env = await self.environments.create(
            organization_id=organization_id, customer_id=customer_id, name=name
        )
        await self.db.commit()
        return env

    async def list_environments(
        self, organization_id: uuid.UUID, customer_id: uuid.UUID
    ) -> list[CustomerEnvironment]:
        await self.get_customer(organization_id, customer_id)
        return await self.environments.list_for_customer(organization_id, customer_id)

    async def get_environment(
        self, organization_id: uuid.UUID, customer_id: uuid.UUID, environment_id: uuid.UUID
    ) -> CustomerEnvironment:
        env = await self.environments.get(organization_id, environment_id)
        if env is None or env.customer_id != customer_id:
            raise NotFoundError("Environment not found.")
        return env

    async def get_environment_overview(
        self, organization_id: uuid.UUID, customer_id: uuid.UUID, environment_id: uuid.UUID
    ) -> EnvironmentOverview:
        env = await self.get_environment(organization_id, customer_id, environment_id)
        services = await self.services.list_for_environment(organization_id, env.id)
        children = []
        for service in services:
            repos = await self.repositories.list_for_service(organization_id, service.id)
            deployments = await self.deployments.list_for_service(organization_id, service.id)
            children.append(
                ServiceWithChildren(service=service, repositories=repos, deployments=deployments)
            )
        return EnvironmentOverview(environment=env, services=children)

    # --- services ----------------------------------------------------

    async def create_service(
        self,
        organization_id: uuid.UUID,
        customer_id: uuid.UUID,
        environment_id: uuid.UUID,
        *,
        name: str,
        language: str | None,
        owner_team: str | None,
    ) -> Service:
        await self.get_environment(organization_id, customer_id, environment_id)
        service = await self.services.create(
            organization_id=organization_id,
            environment_id=environment_id,
            name=name,
            language=language,
            owner_team=owner_team,
        )
        await self.db.commit()
        return service

    async def _get_service_or_404(
        self, organization_id: uuid.UUID, service_id: uuid.UUID
    ) -> Service:
        service = await self.services.get(organization_id, service_id)
        if service is None:
            raise NotFoundError("Service not found.")
        return service

    # --- repositories & deployments (flattened under /services/{id}/...) --

    async def create_repository(
        self,
        organization_id: uuid.UUID,
        service_id: uuid.UUID,
        *,
        provider: RepositoryProvider,
        full_name: str,
        default_branch: str,
    ) -> CodeRepository:
        await self._get_service_or_404(organization_id, service_id)
        repo = await self.repositories.create(
            organization_id=organization_id,
            service_id=service_id,
            provider=provider,
            full_name=full_name,
            default_branch=default_branch,
        )
        await self.db.commit()
        return repo

    async def create_deployment(
        self,
        organization_id: uuid.UUID,
        service_id: uuid.UUID,
        *,
        version: str,
        commit_sha: str | None,
        status: DeploymentStatus,
        deployed_at: datetime | None,
    ) -> Deployment:
        await self._get_service_or_404(organization_id, service_id)
        fields: dict[str, object] = {
            "organization_id": organization_id,
            "service_id": service_id,
            "version": version,
            "commit_sha": commit_sha,
            "status": status,
        }
        if deployed_at is not None:
            fields["deployed_at"] = deployed_at
        deployment = await self.deployments.create(**fields)
        await self.db.commit()
        return deployment
