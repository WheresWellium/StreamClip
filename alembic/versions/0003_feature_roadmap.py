"""Feature roadmap: templates, clip editor, splice, webhooks, feedback."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from backend.db.types import json_server_default

revision = "0003_feature_roadmap"
down_revision = "0002_clip_meme_keywords"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table(
        "job_templates",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column(
            "config_json",
            sa.JSON(),
            nullable=False,
            server_default=json_server_default("{}", bind),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_job_templates_user_id", "job_templates", ["user_id"])

    op.add_column(
        "clips",
        sa.Column(
            "render_overrides",
            sa.JSON(),
            nullable=False,
            server_default=json_server_default("{}", bind),
        ),
    )
    op.add_column("clips", sa.Column("kind", sa.String(32), nullable=False, server_default="discovery"))
    op.add_column(
        "clips",
        sa.Column(
            "parent_clip_ids",
            sa.JSON(),
            nullable=False,
            server_default=json_server_default("[]", bind),
        ),
    )

    op.add_column("users", sa.Column("webhook_url", sa.String(512), nullable=True))
    op.add_column("users", sa.Column("webhook_secret", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("style_weights", sa.JSON(), nullable=True))

    op.create_table(
        "clip_feedback",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("clip_id", sa.String(32), sa.ForeignKey("clips.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_clip_feedback_clip_id", "clip_feedback", ["clip_id"])

    op.add_column("jobs", sa.Column("asset_pack_id", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "asset_pack_id")
    op.drop_index("ix_clip_feedback_clip_id", table_name="clip_feedback")
    op.drop_table("clip_feedback")
    op.drop_column("users", "style_weights")
    op.drop_column("users", "webhook_secret")
    op.drop_column("users", "webhook_url")
    op.drop_column("clips", "parent_clip_ids")
    op.drop_column("clips", "kind")
    op.drop_column("clips", "render_overrides")
    op.drop_index("ix_job_templates_user_id", table_name="job_templates")
    op.drop_table("job_templates")
