"""Track per-device license activation seats."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from backend.db.types import create_foreign_key

revision = "0012_license_activation_seats"
down_revision = "0011_vault_bytes_titles_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "install_license_activations" not in inspector.get_table_names():
        op.create_table(
            "install_license_activations",
            sa.Column("id", sa.String(32), primary_key=True),
            sa.Column("license_id", sa.String(32), nullable=False),
            sa.Column("machine_id", sa.String(128), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="active"),
            sa.Column(
                "activated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "last_seen_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.UniqueConstraint(
                "license_id",
                "machine_id",
                name="uq_install_license_activation_machine",
            ),
        )
        create_foreign_key(
            bind,
            "fk_install_license_activations_license_id",
            "install_license_activations",
            "install_licenses",
            ["license_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_index(
            "ix_install_license_activations_license_id",
            "install_license_activations",
            ["license_id"],
        )
        op.create_index(
            "ix_install_license_activations_machine_id",
            "install_license_activations",
            ["machine_id"],
        )

    # Backfill legacy single-machine activations (idempotent via unique constraint).
    op.execute(
        sa.text(
            """
            INSERT INTO install_license_activations (
                id,
                license_id,
                machine_id,
                status,
                activated_at,
                last_seen_at,
                created_at,
                updated_at
            )
            SELECT
                id,
                id,
                machine_id,
                'active',
                COALESCE(activated_at, CURRENT_TIMESTAMP),
                COALESCE(activated_at, CURRENT_TIMESTAMP),
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            FROM install_licenses
            WHERE machine_id IS NOT NULL
              AND status = 'activated'
              AND NOT EXISTS (
                  SELECT 1
                  FROM install_license_activations a
                  WHERE a.license_id = install_licenses.id
                    AND a.machine_id = install_licenses.machine_id
              )
            """
        )
    )


def downgrade() -> None:
    op.drop_index(
        "ix_install_license_activations_machine_id",
        table_name="install_license_activations",
    )
    op.drop_index(
        "ix_install_license_activations_license_id",
        table_name="install_license_activations",
    )
    op.drop_constraint(
        "fk_install_license_activations_license_id",
        "install_license_activations",
        type_="foreignkey",
    )
    op.drop_table("install_license_activations")
