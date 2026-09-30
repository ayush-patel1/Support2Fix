"""Customer context routes. See system-design.md §7.2/§7.3 and Phase 4.

Like organizations, every route is scoped through `OrgContext` (the
caller's session), never a client-supplied organization id. Repository and
deployment creation are flattened under /services/{service_id}/... rather
than nested five levels deep under /customers/.../environments/.../services;
the service layer still verifies the service belongs to the caller's org.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, get_org_context, require_role
from app.core.db import get_db
from app.models.membership import Role
from app.schemas.customer import (
    CustomerCreate,
    CustomerPublic,
    CustomerUpdate,
    DeploymentCreate,
    DeploymentPublic,
    EnvironmentCreate,
    EnvironmentOverviewPublic,
    EnvironmentPublic,
    RepositoryCreate,
    RepositoryPublic,
    ServiceCreate,
    ServiceOverview,
    ServicePublic,
)
from app.services.customers import CustomerService

router = APIRouter(tags=["customers"])


@router.post("/customers", response_model=CustomerPublic, status_code=201)
async def create_customer(
    body: CustomerCreate,
    ctx: OrgContext = Depends(require_role(Role.SUPPORT)),
    db: AsyncSession = Depends(get_db),
) -> CustomerPublic:
    customer = await CustomerService(db).create_customer(
        ctx.organization_id, name=body.name, external_ref=body.external_ref, tier=body.tier
    )
    return CustomerPublic.model_validate(customer)


@router.get("/customers", response_model=list[CustomerPublic])
async def list_customers(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[CustomerPublic]:
    customers = await CustomerService(db).list_customers(ctx.organization_id)
    return [CustomerPublic.model_validate(c) for c in customers]


@router.get("/customers/{customer_id}", response_model=CustomerPublic)
async def get_customer(
    customer_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> CustomerPublic:
    customer = await CustomerService(db).get_customer(ctx.organization_id, customer_id)
    return CustomerPublic.model_validate(customer)


@router.patch("/customers/{customer_id}", response_model=CustomerPublic)
async def update_customer(
    customer_id: UUID,
    body: CustomerUpdate,
    ctx: OrgContext = Depends(require_role(Role.SUPPORT)),
    db: AsyncSession = Depends(get_db),
) -> CustomerPublic:
    customer = await CustomerService(db).update_customer(
        ctx.organization_id,
        customer_id,
        name=body.name,
        external_ref=body.external_ref,
        tier=body.tier,
    )
    return CustomerPublic.model_validate(customer)


@router.post(
    "/customers/{customer_id}/environments", response_model=EnvironmentPublic, status_code=201
)
async def create_environment(
    customer_id: UUID,
    body: EnvironmentCreate,
    ctx: OrgContext = Depends(require_role(Role.SUPPORT)),
    db: AsyncSession = Depends(get_db),
) -> EnvironmentPublic:
    env = await CustomerService(db).create_environment(
        ctx.organization_id, customer_id, name=body.name
    )
    return EnvironmentPublic.model_validate(env)


@router.get("/customers/{customer_id}/environments", response_model=list[EnvironmentPublic])
async def list_environments(
    customer_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[EnvironmentPublic]:
    envs = await CustomerService(db).list_environments(ctx.organization_id, customer_id)
    return [EnvironmentPublic.model_validate(e) for e in envs]


@router.get(
    "/customers/{customer_id}/environments/{environment_id}",
    response_model=EnvironmentOverviewPublic,
)
async def get_environment_overview(
    customer_id: UUID,
    environment_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> EnvironmentOverviewPublic:
    """Backs the environment overview page: one call returns the

    environment plus every service in it, each with its repositories and
    deployment history — the whole Customer -> Environment -> Service ->
    {Repository, Deployment} chain for this environment.
    """
    overview = await CustomerService(db).get_environment_overview(
        ctx.organization_id, customer_id, environment_id
    )
    return EnvironmentOverviewPublic(
        environment=EnvironmentPublic.model_validate(overview.environment),
        services=[
            ServiceOverview(
                service=ServicePublic.model_validate(s.service),
                repositories=[RepositoryPublic.model_validate(r) for r in s.repositories],
                deployments=[DeploymentPublic.model_validate(d) for d in s.deployments],
            )
            for s in overview.services
        ],
    )


@router.post(
    "/customers/{customer_id}/environments/{environment_id}/services",
    response_model=ServicePublic,
    status_code=201,
)
async def create_service(
    customer_id: UUID,
    environment_id: UUID,
    body: ServiceCreate,
    ctx: OrgContext = Depends(require_role(Role.SUPPORT)),
    db: AsyncSession = Depends(get_db),
) -> ServicePublic:
    service = await CustomerService(db).create_service(
        ctx.organization_id,
        customer_id,
        environment_id,
        name=body.name,
        language=body.language,
        owner_team=body.owner_team,
    )
    return ServicePublic.model_validate(service)


@router.post(
    "/services/{service_id}/repositories", response_model=RepositoryPublic, status_code=201
)
async def create_repository(
    service_id: UUID,
    body: RepositoryCreate,
    ctx: OrgContext = Depends(require_role(Role.SUPPORT)),
    db: AsyncSession = Depends(get_db),
) -> RepositoryPublic:
    repo = await CustomerService(db).create_repository(
        ctx.organization_id,
        service_id,
        provider=body.provider,
        full_name=body.full_name,
        default_branch=body.default_branch,
    )
    return RepositoryPublic.model_validate(repo)


@router.post("/services/{service_id}/deployments", response_model=DeploymentPublic, status_code=201)
async def create_deployment(
    service_id: UUID,
    body: DeploymentCreate,
    ctx: OrgContext = Depends(require_role(Role.SUPPORT)),
    db: AsyncSession = Depends(get_db),
) -> DeploymentPublic:
    deployment = await CustomerService(db).create_deployment(
        ctx.organization_id,
        service_id,
        version=body.version,
        commit_sha=body.commit_sha,
        status=body.status,
        deployed_at=body.deployed_at,
    )
    return DeploymentPublic.model_validate(deployment)
