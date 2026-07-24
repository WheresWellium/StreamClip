"""Vault byte quotas, title audit, feedback attachments, user preferences."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from backend.db.types import (
    add_column,
    create_foreign_key,
    json_server_default,
    portable_json_type,
)

revision = "0011_vault_bytes_titles_feedback"
down_revision = "0010_password_reset_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    add_column(
        bind,
        "vault_clips",
        sa.Column(
            "file_size_bytes",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
    )
    add_column(
        bind,
        "vault_clips",
        sa.Column(
            "archived_flag",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    if bind.dialect.name == "postgresql":
        op.create_index(
            "ix_vault_clips_user_archived",
            "vault_clips",
            ["user_id", "archived_flag"],
            postgresql_where=sa.text("archived_flag = false"),
        )

    add_column(
        bind,
        "users",
        sa.Column(
            "user_preferences",
            portable_json_type(bind),
            nullable=False,
            server_default=json_server_default("{}", bind),
        ),
    )

    add_column(
        bind,
        "bug_reports",
        sa.Column("assigned_to", sa.String(32), nullable=True),
    )
    create_foreign_key(
        bind,
        "fk_bug_reports_assigned_to",
        "bug_reports",
        "users",
        ["assigned_to"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_bug_reports_assigned_to", "bug_reports", ["assigned_to"])

    op.create_table(
        "job_titles_audit",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("job_id", sa.String(32), nullable=False),
        sa.Column("previous_title", sa.String(512), nullable=True),
        sa.Column("new_title", sa.String(512), nullable=True),
        sa.Column("user_id", sa.String(32), nullable=True),
        sa.Column(
            "source",
            sa.String(32),
            nullable=False,
            server_default="user_edit",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    create_foreign_key(
        bind,
        "fk_job_titles_audit_job_id",
        "job_titles_audit",
        "jobs",
        ["job_id"],
        ["id"],
        ondelete="CASCADE",
    )
    create_foreign_key(
        bind,
        "fk_job_titles_audit_user_id",
        "job_titles_audit",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_job_titles_audit_job_id", "job_titles_audit", ["job_id"])
    op.create_index("ix_job_titles_audit_user_id", "job_titles_audit", ["user_id"])

    op.create_table(
        "feedback_attachments",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("bug_report_id", sa.String(32), nullable=True),
        sa.Column("user_id", sa.String(32), nullable=True),
        sa.Column("device_id", sa.String(64), nullable=True),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column(
            "content_type",
            sa.String(128),
            nullable=False,
            server_default="application/octet-stream",
        ),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    create_foreign_key(
        bind,
        "fk_feedback_attachments_bug_report_id",
        "feedback_attachments",
        "bug_reports",
        ["bug_report_id"],
        ["id"],
        ondelete="CASCADE",
    )
    create_foreign_key(
        bind,
        "fk_feedback_attachments_user_id",
        "feedback_attachments",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_feedback_attachments_bug_report_id",
        "feedback_attachments",
        ["bug_report_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("ix_feedback_attachments_bug_report_id", table_name="feedback_attachments")
    op.drop_constraint(
        "fk_feedback_attachments_user_id",
        "feedback_attachments",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_feedback_attachments_bug_report_id",
        "feedback_attachments",
        type_="foreignkey",
    )
    op.drop_table("feedback_attachments")

    op.drop_index("ix_job_titles_audit_user_id", table_name="job_titles_audit")
    op.drop_index("ix_job_titles_audit_job_id", table_name="job_titles_audit")
    op.drop_constraint(
        "fk_job_titles_audit_user_id",
        "job_titles_audit",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_job_titles_audit_job_id",
        "job_titles_audit",
        type_="foreignkey",
    )
    op.drop_table("job_titles_audit")

    op.drop_index("ix_bug_reports_assigned_to", table_name="bug_reports")
    op.drop_constraint(
        "fk_bug_reports_assigned_to",
        "bug_reports",
        type_="foreignkey",
    )
    op.drop_column("bug_reports", "assigned_to")

    op.drop_column("users", "user_preferences")

    if bind.dialect.name == "postgresql":
        op.drop_index("ix_vault_clips_user_archived", table_name="vault_clips")

    op.drop_column("vault_clips", "archived_flag")
    op.drop_column("vault_clips", "file_size_bytes")
