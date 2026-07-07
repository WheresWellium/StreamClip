"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from backend.db.types import drop_pg_enums, json_server_default, portable_json_type


revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    json_type = portable_json_type(bind)

    # ── users ────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255)),
        sa.Column("display_name", sa.String(120)),
        sa.Column("tier", sa.Enum("free", "pro", "admin", name="user_tier"),
                  nullable=False, server_default="free"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("twitch_user_id", sa.String(64), index=True),
        sa.Column("jobs_used_this_month", sa.Integer, nullable=False, server_default="0"),
        sa.Column("minutes_processed_this_month", sa.Float, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # ── jobs ─────────────────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("owner_id", sa.String(32),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), index=True),
        sa.Column("source_url", sa.Text),
        sa.Column("source_storage_key", sa.String(512)),
        sa.Column("source_title", sa.String(512)),
        sa.Column("source_duration_secs", sa.Float),
        sa.Column("source_width", sa.Integer),
        sa.Column("source_height", sa.Integer),
        sa.Column("config_snapshot", json_type, nullable=False,
                  server_default=json_server_default("{}", bind)),
        sa.Column("status",
                  sa.Enum("queued", "ingesting", "transcribing", "detecting",
                          "processing", "done", "error", "cancelled",
                          name="job_status"),
                  nullable=False, server_default="queued", index=True),
        sa.Column("progress", sa.Float, nullable=False, server_default="0"),
        sa.Column("current_stage", sa.String(64), nullable=False, server_default="queued"),
        sa.Column("error_code", sa.String(64)),
        sa.Column("error_message", sa.Text),
        sa.Column("celery_task_id", sa.String(64), index=True),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_jobs_owner_created", "jobs", ["owner_id", "created_at"])

    # ── assets ───────────────────────────────────────────────────────
    op.create_table(
        "assets",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("asset_type", sa.String(16), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("sfx_storage_key", sa.String(512)),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("tags", json_type, nullable=False,
                  server_default=json_server_default("[]", bind)),
        sa.Column("default_duration_secs", sa.Float, nullable=False, server_default="2.5"),
        sa.Column("embedding", json_type),
        sa.Column("owner_id", sa.String(32),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("use_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # ── clips ────────────────────────────────────────────────────────
    op.create_table(
        "clips",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("job_id", sa.String(32),
                  sa.ForeignKey("jobs.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("rank", sa.Integer, nullable=False, server_default="0"),
        sa.Column("start_secs", sa.Float, nullable=False),
        sa.Column("end_secs", sa.Float, nullable=False),
        sa.Column("title", sa.String(255), nullable=False, server_default=""),
        sa.Column("hook", sa.Text, nullable=False, server_default=""),
        sa.Column("emotion", sa.String(32), nullable=False, server_default="neutral"),
        sa.Column("transcript_text", sa.Text, nullable=False, server_default=""),
        sa.Column("llm_reason", sa.Text, nullable=False, server_default=""),
        sa.Column("ensemble_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("llm_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("audio_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("spectral_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("flow_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("chat_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("raw_storage_key", sa.String(512)),
        sa.Column("vertical_storage_key", sa.String(512)),
        sa.Column("captioned_storage_key", sa.String(512)),
        sa.Column("final_storage_key", sa.String(512)),
        sa.Column("thumbnail_storage_key", sa.String(512)),
        sa.Column("duration_secs", sa.Float, nullable=False, server_default="0"),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("status",
                  sa.Enum("pending", "processing", "done", "error", name="clip_status"),
                  nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text),
        sa.Column("render_time_secs", sa.Float, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_clips_job_rank", "clips", ["job_id", "rank"])

    # ── clip_overlays ────────────────────────────────────────────────
    op.create_table(
        "clip_overlays",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("clip_id", sa.String(32),
                  sa.ForeignKey("clips.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("asset_id", sa.String(32),
                  sa.ForeignKey("assets.id", ondelete="SET NULL")),
        sa.Column("trigger_time_secs", sa.Float, nullable=False),
        sa.Column("duration_secs", sa.Float, nullable=False),
        sa.Column("position", sa.String(32), nullable=False, server_default="top_right"),
        sa.Column("similarity_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("matched_keyword", sa.String(255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_table("clip_overlays")
    op.drop_table("clips")
    op.drop_table("assets")
    op.drop_table("jobs")
    op.drop_table("users")
    drop_pg_enums(bind, "clip_status", "job_status", "user_tier")
