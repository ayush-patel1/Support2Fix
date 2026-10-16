"""phase 9: durable investigations and worker queue

Revision ID: 31c28f4a0b71
Revises: 8c27f6b5a1d0
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "31c28f4a0b71"
down_revision: str | None = "8c27f6b5a1d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    investigation_status = sa.Enum(
        "QUEUED", "RUNNING", "COMPLETED", "FAILED", name="investigation_status"
    )
    investigation_event_type = sa.Enum(
        "QUEUED",
        "STARTED",
        "TOOL_COMPLETED",
        "COMPLETED",
        "FAILED",
        name="investigation_event_type",
    )
    investigation_status.create(op.get_bind())
    investigation_event_type.create(op.get_bind())

    op.create_table(
        "investigations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", investigation_status, nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("candidate", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "evidence_gaps",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["started_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["ticket_id", "organization_id"],
            ["tickets.id", "tickets.organization_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_investigations_id_org"),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_investigations_idempotency"
        ),
    )
    op.create_index(
        "ix_investigations_org_created",
        "investigations",
        ["organization_id", "created_at"],
    )
    op.create_index("ix_investigations_organization_id", "investigations", ["organization_id"])
    op.create_index("ix_investigations_ticket_id", "investigations", ["ticket_id"])
    op.create_index("ix_investigations_status", "investigations", ["status"])

    op.create_table(
        "investigation_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", investigation_event_type, nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["investigation_id", "organization_id"],
            ["investigations.id", "investigations.organization_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_investigation_events_order",
        "investigation_events",
        ["investigation_id", "created_at"],
    )
    op.create_index(
        "ix_investigation_events_organization_id",
        "investigation_events",
        ["organization_id"],
    )
    op.create_index(
        "ix_investigation_events_investigation_id",
        "investigation_events",
        ["investigation_id"],
    )

    op.create_table(
        "investigation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="QUEUED", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "run_after",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=100), nullable=True),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["investigation_id", "organization_id"],
            ["investigations.id", "investigations.organization_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("investigation_id"),
    )
    op.create_index(
        "ix_investigation_jobs_ready", "investigation_jobs", ["status", "run_after"]
    )
    op.create_index(
        "ix_investigation_jobs_organization_id",
        "investigation_jobs",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_investigation_jobs_organization_id", table_name="investigation_jobs")
    op.drop_index("ix_investigation_jobs_ready", table_name="investigation_jobs")
    op.drop_table("investigation_jobs")
    op.drop_index(
        "ix_investigation_events_investigation_id", table_name="investigation_events"
    )
    op.drop_index("ix_investigation_events_organization_id", table_name="investigation_events")
    op.drop_index("ix_investigation_events_order", table_name="investigation_events")
    op.drop_table("investigation_events")
    op.drop_index("ix_investigations_status", table_name="investigations")
    op.drop_index("ix_investigations_ticket_id", table_name="investigations")
    op.drop_index("ix_investigations_organization_id", table_name="investigations")
    op.drop_index("ix_investigations_org_created", table_name="investigations")
    op.drop_table("investigations")
    sa.Enum(name="investigation_event_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="investigation_status").drop(op.get_bind(), checkfirst=True)
