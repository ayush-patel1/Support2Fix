import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.ids import uuid7


class Role(enum.StrEnum):
    ADMIN = "ADMIN"
    ENGINEER = "ENGINEER"
    SUPPORT = "SUPPORT"
    VIEWER = "VIEWER"


# A simple hierarchy for `require_role(min_role)` checks (security.md §4).
# Some capabilities split ADMIN/ENGINEER from SUPPORT in ways this linear
# order doesn't capture (e.g. approving a fix is ENGINEER+ADMIN but not
# SUPPORT, even though SUPPORT sits "above" VIEWER) — those routes use
# `require_any_role(...)` instead. See app/api/deps.py.
ROLE_ORDER: dict[Role, int] = {
    Role.VIEWER: 0,
    Role.SUPPORT: 1,
    Role.ENGINEER: 2,
    Role.ADMIN: 3,
}


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_membership_user_org"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[Role] = mapped_column(Enum(Role, name="membership_role", native_enum=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
