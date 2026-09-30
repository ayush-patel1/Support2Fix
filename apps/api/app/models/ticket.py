"""Support tickets and their timeline. See docs/architecture/system-design.md

§5.2 for the status state machine this model backs — `TicketService`
(app/services/tickets.py) is what actually enforces the allowed
transitions; this file just defines the shape.
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
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.ids import uuid7


class TicketPriority(enum.StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TicketStatus(enum.StrEnum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    ROOT_CAUSE_FOUND = "ROOT_CAUSE_FOUND"
    FIX_PROPOSED = "FIX_PROPOSED"
    VALIDATING = "VALIDATING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class TicketEventType(enum.StrEnum):
    CREATED = "CREATED"
    FIELD_CHANGED = "FIELD_CHANGED"
    STATUS_CHANGED = "STATUS_CHANGED"
    COMMENT = "COMMENT"


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        ForeignKeyConstraint(
            ["customer_id", "organization_id"],
            ["customers.id", "customers.organization_id"],
            ondelete="RESTRICT",  # don't let a customer vanish out from under open tickets
        ),
        UniqueConstraint("id", "organization_id", name="uq_tickets_id_org"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, name="ticket_priority"), default=TicketPriority.MEDIUM
    )
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status"), default=TicketStatus.OPEN, index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TicketEvent(Base):
    """An immutable timeline entry. Written by TicketService, never edited

    or deleted — the timeline is a record of what happened, not a mutable
    field.
    """

    __tablename__ = "ticket_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["ticket_id", "organization_id"],
            ["tickets.id", "tickets.organization_id"],
            ondelete="CASCADE",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[TicketEventType] = mapped_column(Enum(TicketEventType, name="ticket_event_type"))
    # e.g. {"from": "OPEN", "to": "INVESTIGATING"} or {"comment": "..."} or
    # {"field": "priority", "from": "LOW", "to": "HIGH"}
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
