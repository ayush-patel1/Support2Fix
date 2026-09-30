import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.customer import CustomerTier, DeploymentStatus, RepositoryProvider


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    external_ref: str | None = Field(default=None, max_length=200)
    tier: CustomerTier = CustomerTier.STANDARD


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    external_ref: str | None = None
    tier: CustomerTier | None = None


class CustomerPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    external_ref: str | None
    tier: CustomerTier
    created_at: datetime


class EnvironmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class EnvironmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    name: str
    created_at: datetime


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    language: str | None = Field(default=None, max_length=50)
    owner_team: str | None = Field(default=None, max_length=100)


class ServicePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    environment_id: uuid.UUID
    name: str
    language: str | None
    owner_team: str | None


class RepositoryCreate(BaseModel):
    provider: RepositoryProvider = RepositoryProvider.LOCAL
    full_name: str = Field(min_length=1, max_length=300)
    default_branch: str = Field(default="main", max_length=100)


class RepositoryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    service_id: uuid.UUID
    provider: RepositoryProvider
    full_name: str
    default_branch: str


class DeploymentCreate(BaseModel):
    version: str = Field(min_length=1, max_length=100)
    commit_sha: str | None = Field(default=None, max_length=64)
    status: DeploymentStatus = DeploymentStatus.SUCCESS
    deployed_at: datetime | None = None


class DeploymentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    service_id: uuid.UUID
    version: str
    commit_sha: str | None
    status: DeploymentStatus
    deployed_at: datetime


class ServiceOverview(BaseModel):
    service: ServicePublic
    repositories: list[RepositoryPublic]
    deployments: list[DeploymentPublic]


class EnvironmentOverviewPublic(BaseModel):
    environment: EnvironmentPublic
    services: list[ServiceOverview]
