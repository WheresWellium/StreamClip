"""Add meme_keywords JSON column to clips."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_clip_meme_keywords"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "clips",
        sa.Column("meme_keywords", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("clips", "meme_keywords")
