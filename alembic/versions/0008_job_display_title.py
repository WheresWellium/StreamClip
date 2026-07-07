"""Add user-editable job display_title."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_job_display_title"
down_revision = "0007_license_issuance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("display_title", sa.String(512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("jobs", "display_title")
