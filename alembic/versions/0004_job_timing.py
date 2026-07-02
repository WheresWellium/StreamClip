"""Job timing: pipeline_started_at and stage_durations_json."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_job_timing"
down_revision = "0003_feature_roadmap"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("pipeline_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("stage_durations_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("jobs", "stage_durations_json")
    op.drop_column("jobs", "pipeline_started_at")
