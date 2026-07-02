"""Device identity, licensing, and distribution tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_device_identity"
down_revision = "0004_job_timing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "local_devices",
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
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("onboarding_complete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "claimed_by_user_id",
            sa.String(32),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_local_devices_claimed_by_user_id", "local_devices", ["claimed_by_user_id"])

    op.add_column(
        "jobs",
        sa.Column(
            "device_id",
            sa.String(32),
            sa.ForeignKey("local_devices.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_jobs_device_id", "jobs", ["device_id"])

    user_tier_enum = postgresql.ENUM(
        "free", "pro", "admin", name="user_tier", create_type=False,
    )
    op.create_table(
        "install_licenses",
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
        sa.Column("license_key_hash", sa.String(64), nullable=False),
        sa.Column("machine_id", sa.String(128), nullable=False),
        sa.Column("tier", user_tier_enum, nullable=False, server_default="pro"),
        sa.Column("entitlement_jwt", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "activated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_install_licenses_license_key_hash", "install_licenses", ["license_key_hash"], unique=True)
    op.create_index("ix_install_licenses_machine_id", "install_licenses", ["machine_id"])

    op.add_column(
        "clips",
        sa.Column(
            "approval_status",
            sa.String(16),
            nullable=False,
            server_default="draft",
        ),
    )

    op.create_table(
        "platform_connections",
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
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("account_label", sa.String(255), nullable=False, server_default=""),
        sa.Column("access_token_enc", sa.Text(), nullable=True),
        sa.Column("refresh_token_enc", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("ix_platform_connections_user_id", "platform_connections", ["user_id"])

    op.create_table(
        "publish_jobs",
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
            "clip_id",
            sa.String(32),
            sa.ForeignKey("clips.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "connection_id",
            sa.String(32),
            sa.ForeignKey("platform_connections.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("title", sa.String(255), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_publish_jobs_clip_id", "publish_jobs", ["clip_id"])
    op.create_index("ix_publish_jobs_connection_id", "publish_jobs", ["connection_id"])


def downgrade() -> None:
    op.drop_index("ix_publish_jobs_connection_id", table_name="publish_jobs")
    op.drop_index("ix_publish_jobs_clip_id", table_name="publish_jobs")
    op.drop_table("publish_jobs")
    op.drop_index("ix_platform_connections_user_id", table_name="platform_connections")
    op.drop_table("platform_connections")
    op.drop_column("clips", "approval_status")
    op.drop_index("ix_install_licenses_machine_id", table_name="install_licenses")
    op.drop_index("ix_install_licenses_license_key_hash", table_name="install_licenses")
    op.drop_table("install_licenses")
    op.drop_index("ix_jobs_device_id", table_name="jobs")
    op.drop_column("jobs", "device_id")
    op.drop_index("ix_local_devices_claimed_by_user_id", table_name="local_devices")
    op.drop_table("local_devices")
