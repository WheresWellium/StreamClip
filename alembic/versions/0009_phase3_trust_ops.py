"""Phase 3: license-user linkage, bug reports, data contribution opt-in."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from backend.db.types import add_column, create_foreign_key

revision = "0009_phase3_trust_ops"
down_revision = "0008_job_display_title"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # 3a — link install licenses to the master user identity
    add_column(bind, "install_licenses", sa.Column("user_id", sa.String(32), nullable=True))
    create_foreign_key(
        bind,
        "fk_install_licenses_user_id",
        "install_licenses",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_install_licenses_user_id", "install_licenses", ["user_id"],
    )

    # 3c — training data contribution opt-in (default off)
    add_column(
        bind,
        "users",
        sa.Column(
            "data_contribution_opt_in",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # 3b — bug reports
    op.create_table(
        "bug_reports",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(32),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("device_id", sa.String(64), nullable=True),
        sa.Column(
            "job_id",
            sa.String(32),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("categories", sa.JSON(), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("environment", sa.JSON(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_bug_reports_user_id", "bug_reports", ["user_id"])
    op.create_index("ix_bug_reports_job_id", "bug_reports", ["job_id"])


def downgrade() -> None:
    op.drop_table("bug_reports")
    op.drop_column("users", "data_contribution_opt_in")
    op.drop_index("ix_install_licenses_user_id", table_name="install_licenses")
    op.drop_constraint(
        "fk_install_licenses_user_id", "install_licenses", type_="foreignkey",
    )
    op.drop_column("install_licenses", "user_id")
