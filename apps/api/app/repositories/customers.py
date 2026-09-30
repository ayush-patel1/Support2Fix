"""Data access for the Customer -> Environment -> Service ->

{Repository, Deployment} hierarchy. Every method takes `organization_id`
explicitly and filters on it — the composite FKs on these tables enforce
the same thing at the database level, but the query itself must still be
scoped, or a query with no WHERE clause on organization_id would just
return every organization's rows.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import CodeRepository, Customer, CustomerEnvironment, Deployment, Service


class CustomerRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, organization_id: uuid.UUID, customer_id: uuid.UUID) -> Customer | None:
        stmt = select(Customer).where(
            Customer.id == customer_id, Customer.organization_id == organization_id
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list(self, organization_id: uuid.UUID) -> list[Customer]:
        stmt = (
            select(Customer)
            .where(Customer.organization_id == organization_id)
            .order_by(Customer.name)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def create(self, **fields: object) -> Customer:
        customer = Customer(**fields)
        self.db.add(customer)
        await self.db.flush()
        return customer

    async def update(self, customer: Customer, **fields: object) -> Customer:
        for key, value in fields.items():
            setattr(customer, key, value)
        await self.db.flush()
        return customer


class CustomerEnvironmentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(
        self, organization_id: uuid.UUID, environment_id: uuid.UUID
    ) -> CustomerEnvironment | None:
        stmt = select(CustomerEnvironment).where(
            CustomerEnvironment.id == environment_id,
            CustomerEnvironment.organization_id == organization_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_for_customer(
        self, organization_id: uuid.UUID, customer_id: uuid.UUID
    ) -> list[CustomerEnvironment]:
        stmt = (
            select(CustomerEnvironment)
            .where(
                CustomerEnvironment.customer_id == customer_id,
                CustomerEnvironment.organization_id == organization_id,
            )
            .order_by(CustomerEnvironment.name)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def create(self, **fields: object) -> CustomerEnvironment:
        env = CustomerEnvironment(**fields)
        self.db.add(env)
        await self.db.flush()
        return env


class ServiceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, organization_id: uuid.UUID, service_id: uuid.UUID) -> Service | None:
        stmt = select(Service).where(
            Service.id == service_id, Service.organization_id == organization_id
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_for_environment(
        self, organization_id: uuid.UUID, environment_id: uuid.UUID
    ) -> list[Service]:
        stmt = (
            select(Service)
            .where(
                Service.environment_id == environment_id, Service.organization_id == organization_id
            )
            .order_by(Service.name)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def create(self, **fields: object) -> Service:
        service = Service(**fields)
        self.db.add(service)
        await self.db.flush()
        return service


class CodeRepositoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_service(
        self, organization_id: uuid.UUID, service_id: uuid.UUID
    ) -> list[CodeRepository]:
        stmt = (
            select(CodeRepository)
            .where(
                CodeRepository.service_id == service_id,
                CodeRepository.organization_id == organization_id,
            )
            .order_by(CodeRepository.full_name)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def create(self, **fields: object) -> CodeRepository:
        repo = CodeRepository(**fields)
        self.db.add(repo)
        await self.db.flush()
        return repo


class DeploymentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_service(
        self, organization_id: uuid.UUID, service_id: uuid.UUID
    ) -> list[Deployment]:
        stmt = (
            select(Deployment)
            .where(
                Deployment.service_id == service_id, Deployment.organization_id == organization_id
            )
            .order_by(Deployment.deployed_at.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def create(self, **fields: object) -> Deployment:
        deployment = Deployment(**fields)
        self.db.add(deployment)
        await self.db.flush()
        return deployment
