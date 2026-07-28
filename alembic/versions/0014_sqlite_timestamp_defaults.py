"""Replace Postgres-only now() defaults with CURRENT_TIMESTAMP on SQLite."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from backend.db.types import alter_column

revision = "0014_sqlite_timestamp_defaults"
down_revision = "0012_license_activation_seats"
branch_labels = None
depends_on = None

# Tables created with sa.text("now()") in early migrations — invalid on SQLite.
_SQLITE_TIMESTAMP_FIXES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("job_templates", ("created_at", "updated_at")),
    ("clip_feedback", ("created_at", "updated_at")),
    ("local_devices", ("created_at", "updated_at", "last_seen_at")),
    ("platform_connections", ("created_at", "updated_at")),
    ("vault_clips", ("created_at", "updated_at", "saved_at")),
    ("install_oauth_apps", ("updated_at",)),
    ("publish_jobs", ("created_at", "updated_at")),
    ("install_licenses", ("created_at", "updated_at")),
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        return
    current = sa.text("CURRENT_TIMESTAMP")
    for table, columns in _SQLITE_TIMESTAMP_FIXES:
        for column in columns:
            alter_column(bind, table, column, server_default=current)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        return
    pg_now = sa.text("now()")
    for table, columns in _SQLITE_TIMESTAMP_FIXES:
        for column in columns:
            alter_column(bind, table, column, server_default=pg_now)
