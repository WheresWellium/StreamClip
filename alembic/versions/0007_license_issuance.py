"""License issuance: commerce-issued keys precede machine activation."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from backend.db.types import add_column, alter_column

revision = "0007_license_issuance"
down_revision = "0006_distribution_vault"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    alter_column(bind, "install_licenses", "machine_id", existing_type=sa.String(128), nullable=True)
    alter_column(bind, "install_licenses", "entitlement_jwt", existing_type=sa.Text(), nullable=True)
    alter_column(
        bind,
        "install_licenses",
        "activated_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
        server_default=None,
    )
    add_column(
        bind,
        "install_licenses",
        sa.Column("status", sa.String(16), nullable=False, server_default="issued"),
    )
    add_column(bind, "install_licenses", sa.Column("order_id", sa.String(64), nullable=True))
    add_column(bind, "install_licenses", sa.Column("customer_email", sa.String(320), nullable=True))
    add_column(
        bind,
        "install_licenses",
        sa.Column("activation_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_install_licenses_order_id", "install_licenses", ["order_id"])

    # Rows that pre-date issuance tracking were created by direct activation.
    op.execute(
        "UPDATE install_licenses SET status = 'activated', activation_count = 1 "
        "WHERE entitlement_jwt IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_index("ix_install_licenses_order_id", table_name="install_licenses")
    op.drop_column("install_licenses", "activation_count")
    op.drop_column("install_licenses", "customer_email")
    op.drop_column("install_licenses", "order_id")
    op.drop_column("install_licenses", "status")
    op.alter_column(
        "install_licenses",
        "activated_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )
    op.alter_column("install_licenses", "entitlement_jwt", existing_type=sa.Text(), nullable=False)
    op.alter_column("install_licenses", "machine_id", existing_type=sa.String(128), nullable=False)
