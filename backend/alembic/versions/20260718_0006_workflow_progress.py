"""Add current_step to workflow runs."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260718_0006"
down_revision: str | None = "20260718_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column("current_step", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workflow_runs", "current_step")
