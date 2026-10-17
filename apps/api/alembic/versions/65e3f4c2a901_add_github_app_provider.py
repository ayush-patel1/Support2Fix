"""Add the GitHub App integration provider.

Revision ID: 65e3f4c2a901
Revises: 31c28f4a0b71
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "65e3f4c2a901"
down_revision: str | None = "31c28f4a0b71"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE integration_provider ADD VALUE IF NOT EXISTS 'GITHUB_APP'")
    op.add_column(
        "tickets",
        sa.Column("code_host_integration_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        "ix_tickets_code_host_integration_id", "tickets", ["code_host_integration_id"]
    )
    op.create_foreign_key(
        "fk_tickets_code_host_integration_org",
        "tickets",
        "integrations",
        ["code_host_integration_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="SET NULL (code_host_integration_id)",
    )


def downgrade() -> None:
    op.drop_constraint("fk_tickets_code_host_integration_org", "tickets", type_="foreignkey")
    op.drop_index("ix_tickets_code_host_integration_id", table_name="tickets")
    op.drop_column("tickets", "code_host_integration_id")
    # PostgreSQL cannot remove an enum value without rebuilding the type.
    # Keep the value so a downgrade never invalidates existing integrations.
    op.drop_constraint("fk_tickets_code_host_integration_org", "tickets", type_="foreignkey")
    op.drop_index("ix_tickets_code_host_integration_id", table_name="tickets")
    op.drop_column("tickets", "code_host_integration_id")
