"""Track the start of each user's quota period so monthly counters reset."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from backend.db.types import add_column

revision = "0012_quota_period_start"
down_revision = "0011_vault_bytes_titles_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    add_column(
        bind,
        "users",
        sa.Column("quota_period_start", sa.DateTime(timezone=True), nullable=True),
    )
    # Existing rows start their first tracked period now, so historical
    # counters are not treated as an expired period and wiped unexpectedly.
    op.execute(
        sa.text(
            "UPDATE users SET quota_period_start = CURRENT_TIMESTAMP "
            "WHERE quota_period_start IS NULL",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "quota_period_start")
