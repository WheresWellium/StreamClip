"""Password reset tokens for forgot-password flow."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from backend.db.types import create_foreign_key

revision = "0010_password_reset_tokens"
down_revision = "0009_phase3_trust_ops"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    create_foreign_key(
        bind,
        "fk_password_reset_tokens_user_id",
        "password_reset_tokens",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"],
    )
    op.create_index(
        "ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("password_reset_tokens")
