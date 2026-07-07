"""Distribution hardening and clip vault."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from backend.db.types import add_column, alter_column, create_foreign_key, json_server_default

revision = "0006_distribution_vault"
down_revision = "0005_device_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table(
        "vault_clips",
        sa.Column("id", sa.String(32), primary_key=True),
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
        sa.Column(
            "user_id",
            sa.String(32),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_clip_id",
            sa.String(32),
            sa.ForeignKey("clips.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_job_id", sa.String(32), nullable=True),
        sa.Column("title", sa.String(255), nullable=False, server_default=""),
        sa.Column("hook", sa.Text(), nullable=False, server_default=""),
        sa.Column("duration_secs", sa.Float(), nullable=False, server_default="0"),
        sa.Column("storage_key", sa.String(512), nullable=True),
        sa.Column("thumb_storage_key", sa.String(512), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="copying"),
        sa.Column(
            "metadata_json",
            sa.JSON(),
            nullable=False,
            server_default=json_server_default("{}", bind),
        ),
        sa.Column(
            "saved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_vault_clips_user_id", "vault_clips", ["user_id"])
    op.create_index("ix_vault_clips_source_clip_id", "vault_clips", ["source_clip_id"])

    op.create_table(
        "install_oauth_apps",
        sa.Column("platform", sa.String(32), primary_key=True),
        sa.Column("client_id", sa.Text(), nullable=False, server_default=""),
        sa.Column("client_secret_enc", sa.Text(), nullable=True),
        sa.Column("redirect_uri", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    alter_column(bind, "publish_jobs", "clip_id", existing_type=sa.String(32), nullable=True)
    add_column(bind, "publish_jobs", sa.Column("vault_clip_id", sa.String(32), nullable=True))
    add_column(bind, "publish_jobs", sa.Column("external_url", sa.Text(), nullable=True))
    add_column(bind, "publish_jobs", sa.Column("idempotency_key", sa.String(64), nullable=True))
    add_column(
        bind,
        "publish_jobs",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    add_column(bind, "publish_jobs", sa.Column("last_error_code", sa.String(64), nullable=True))
    create_foreign_key(
        bind,
        "fk_publish_jobs_vault_clip_id",
        "publish_jobs",
        "vault_clips",
        ["vault_clip_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_publish_jobs_vault_clip_id", "publish_jobs", ["vault_clip_id"])
    op.create_index(
        "uq_publish_jobs_idempotency_key",
        "publish_jobs",
        ["idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_publish_jobs_idempotency_key", table_name="publish_jobs")
    op.drop_index("ix_publish_jobs_vault_clip_id", table_name="publish_jobs")
    op.drop_constraint("fk_publish_jobs_vault_clip_id", "publish_jobs", type_="foreignkey")
    op.drop_column("publish_jobs", "last_error_code")
    op.drop_column("publish_jobs", "attempt_count")
    op.drop_column("publish_jobs", "idempotency_key")
    op.drop_column("publish_jobs", "external_url")
    op.drop_column("publish_jobs", "vault_clip_id")
    op.alter_column("publish_jobs", "clip_id", existing_type=sa.String(32), nullable=False)

    op.drop_table("install_oauth_apps")
    op.drop_index("ix_vault_clips_source_clip_id", table_name="vault_clips")
    op.drop_index("ix_vault_clips_user_id", table_name="vault_clips")
    op.drop_table("vault_clips")
