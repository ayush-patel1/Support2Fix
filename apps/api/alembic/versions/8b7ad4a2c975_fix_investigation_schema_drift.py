"""Fix investigation schema drift for durable workflow columns.

Revision ID: 8b7ad4a2c975
Revises: 65e3f4c2a901
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8b7ad4a2c975"
down_revision: str | None = "65e3f4c2a901"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "investigations",
        sa.Column("graph_thread_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "investigations",
        sa.Column("budget_used", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "investigations",
        sa.Column("error", sa.String(length=1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("investigations", "error")
    op.drop_column("investigations", "budget_used")
    op.drop_column("investigations", "graph_thread_id")
