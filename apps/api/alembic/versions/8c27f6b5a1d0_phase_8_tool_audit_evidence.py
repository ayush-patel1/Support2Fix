"""phase 8: tool call audit and evidence

Revision ID: 8c27f6b5a1d0
Revises: d5ad3d246dd3
Create Date: 2026-10-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8c27f6b5a1d0"
down_revision: str | None = "d5ad3d246dd3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tool_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("integration_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tool_name", sa.String(length=200), nullable=False),
        sa.Column("risk", sa.String(length=16), nullable=False),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("arguments", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result_sha256", sa.String(length=64), nullable=True),
        sa.Column("error", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["integration_id", "organization_id"],
            ["integrations.id", "integrations.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_tool_calls_id_org"),
    )
    op.create_index("ix_tool_calls_organization_id", "tool_calls", ["organization_id"])
    op.create_index("ix_tool_calls_actor_id", "tool_calls", ["actor_id"])

    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tool_call_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("source_ref", sa.String(length=500), nullable=True),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tool_call_id", "organization_id"],
            ["tool_calls.id", "tool_calls.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_organization_id", "evidence", ["organization_id"])

    op.execute(
        """
        CREATE FUNCTION reject_tool_record_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'tool audit and evidence records are immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in ("tool_calls", "evidence"):
        op.execute(
            f"CREATE TRIGGER {table}_immutable "
            f"BEFORE UPDATE OR DELETE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION reject_tool_record_mutation()"
        )


def downgrade() -> None:
    op.execute("DROP TRIGGER evidence_immutable ON evidence")
    op.execute("DROP TRIGGER tool_calls_immutable ON tool_calls")
    op.execute("DROP FUNCTION reject_tool_record_mutation()")
    op.drop_index("ix_evidence_organization_id", table_name="evidence")
    op.drop_table("evidence")
    op.drop_index("ix_tool_calls_actor_id", table_name="tool_calls")
    op.drop_index("ix_tool_calls_organization_id", table_name="tool_calls")
    op.drop_table("tool_calls")
