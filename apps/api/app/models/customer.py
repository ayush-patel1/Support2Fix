"""Customer context: Customer -> Environment -> Service -> {Repository,

Deployment}. See docs/architecture/system-design.md §6 and Phase 4.

Every child table here uses a **composite foreign key** `(parent_id,
organization_id)` pointing at the parent's `(id, organization_id)`, not just
`parent_id` alone — the tenant-isolation pattern promised in
system-design.md ("the first point where the composite-FK pattern gets
introduced, Phase 3+"). It makes a service row from org A referencing an
environment from org B a constraint violation at the database level, not
just an application bug someone has to catch in code.
"""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.ids import uuid7


class CustomerTier(enum.StrEnum):
    FREE = "FREE"
    STANDARD = "STANDARD"
    ENTERPRISE = "ENTERPRISE"


class DeploymentStatus(enum.StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class RepositoryProvider(enum.StrEnum):
    LOCAL = "LOCAL"  # the default local-git adapter — see ADR-001 D13
    GITHUB = "GITHUB"
    GITLAB = "GITLAB"


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("id", "organization_id", name="uq_customers_id_org"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    external_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tier: Mapped[CustomerTier] = mapped_column(
        Enum(CustomerTier, name="customer_tier"), default=CustomerTier.STANDARD
    )
    # "metadata" is reserved on declarative models (Base.metadata) — see
    # organizations.settings for the same workaround.
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CustomerEnvironment(Base):
    __tablename__ = "customer_environments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["customer_id", "organization_id"],
            ["customers.id", "customers.organization_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("customer_id", "name", name="uq_environment_customer_name"),
        UniqueConstraint("id", "organization_id", name="uq_environments_id_org"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    name: Mapped[str] = mapped_column(String(100))  # e.g. "production", "staging"
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Service(Base):
    __tablename__ = "services"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "organization_id"],
            ["customer_environments.id", "customer_environments.organization_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("environment_id", "name", name="uq_service_environment_name"),
        UniqueConstraint("id", "organization_id", name="uq_services_id_org"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    environment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    name: Mapped[str] = mapped_column(String(150))
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner_team: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CodeRepository(Base):
    """A service's source repository. Named `CodeRepository` (table

    `code_repositories`), not `Repository`, to avoid colliding with the
    unrelated repository *pattern* classes in app/repositories/.
    """

    __tablename__ = "code_repositories"
    __table_args__ = (
        ForeignKeyConstraint(
            ["service_id", "organization_id"],
            ["services.id", "services.organization_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("id", "organization_id", name="uq_code_repositories_id_org"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    provider: Mapped[RepositoryProvider] = mapped_column(
        Enum(RepositoryProvider, name="repository_provider"), default=RepositoryProvider.LOCAL
    )
    full_name: Mapped[str] = mapped_column(String(300))  # e.g. "acme/checkout-service"
    default_branch: Mapped[str] = mapped_column(String(100), default="main", server_default="main")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Deployment(Base):
    __tablename__ = "deployments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["service_id", "organization_id"],
            ["services.id", "services.organization_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("id", "organization_id", name="uq_deployments_id_org"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    version: Mapped[str] = mapped_column(String(100))
    commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[DeploymentStatus] = mapped_column(
        Enum(DeploymentStatus, name="deployment_status"), default=DeploymentStatus.SUCCESS
    )
    deployed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
