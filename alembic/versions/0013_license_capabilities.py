"""Add optional capabilities JSON to install_licenses."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from backend.db.types import add_column

revision = "0013_license_capabilities"
down_revision = "0012_quota_period_start"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    add_column(
        bind,
        "install_licenses",
        sa.Column("capabilities", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("install_licenses", "capabilities")
