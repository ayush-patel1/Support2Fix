"""An organization's configured adapters — one row per (org, kind, provider)

instance. See system-design.md §6 (`integrations` table) and §8 (the five
interfaces this configures: CodeHost, LogSource, DataSource,
DeploymentSource, SupportSource).

`config` holds whatever a given (kind, provider) adapter needs to connect
(a filesystem path for the local adapters today; a base URL/org name for a
real vendor adapter later) — never a secret. `secret_ref` is reserved for
that: a pointer into the secret store (security.md §"secrets": AWS Secrets
Manager + KMS), resolved server-side only, never round-tripped through the
API. The local adapters need no credentials, so it's unused until a real
vendor adapter (Phase 15+) needs one.
"""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.ids import uuid7


class IntegrationKind(enum.StrEnum):
    CODE_HOST = "CODE_HOST"
    LOG_SOURCE = "LOG_SOURCE"
    DATA_SOURCE = "DATA_SOURCE"
    DEPLOYMENT_SOURCE = "DEPLOYMENT_SOURCE"
    SUPPORT_SOURCE = "SUPPORT_SOURCE"


class IntegrationProvider(enum.StrEnum):
    LOCAL = "LOCAL"  # the only adapters built so far — see ADR-001 D13


class Integration(Base):
    __tablename__ = "integrations"
    __table_args__ = (UniqueConstraint("id", "organization_id", name="uq_integrations_id_org"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[IntegrationKind] = mapped_column(Enum(IntegrationKind, name="integration_kind"))
    provider: Mapped[IntegrationProvider] = mapped_column(
        Enum(IntegrationProvider, name="integration_provider"), default=IntegrationProvider.LOCAL
    )
    name: Mapped[str] = mapped_column(String(150))
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    secret_ref: Mapped[str | None] = mapped_column(String(300), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
