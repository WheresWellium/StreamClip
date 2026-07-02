"""
StreamClip — Database Models (SQLAlchemy 2.0)

Async ORM models using the modern Mapped[] typing API.
Every row is uniquely identified by a ULID (sortable + URL-safe).

Tables:
  • users          — Auth principal (optional in dev)
  • jobs           — One row per pipeline run
  • clips          — Generated clip metadata (FK → jobs)
  • clip_overlays  — Per-clip overlay records (FK → clips)
  • assets         — Asset vault entries for the semantic matcher
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ─── Base ────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """Common base for all ORM models."""
    type_annotation_map = {dict[str, Any]: JSONB}


def _ulid() -> str:
    """Generate a sortable, URL-safe ID. Uses uuid4 if ulid lib missing."""
    try:
        from ulid import ULID
        return str(ULID())
    except ImportError:
        return uuid.uuid4().hex


# ─── Enums ──────────────────────────────────────────────────────────────────

class JobStatus(str, Enum):
    QUEUED      = "queued"
    INGESTING   = "ingesting"
    TRANSCRIBING = "transcribing"
    DETECTING   = "detecting"
    PROCESSING  = "processing"
    DONE        = "done"
    ERROR       = "error"
    CANCELLED   = "cancelled"


class ClipStatus(str, Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    DONE       = "done"
    ERROR      = "error"


class UserTier(str, Enum):
    FREE   = "free"
    PRO    = "pro"
    ADMIN  = "admin"


class ApprovalStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    """Map Python enums to DB string values (not member names)."""
    return [member.value for member in enum_cls]


# ─── Mixins ─────────────────────────────────────────────────────────────────

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )


class IDMixin:
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_ulid)


# ─── Models ─────────────────────────────────────────────────────────────────

class User(Base, IDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(120))
    tier: Mapped[UserTier] = mapped_column(
        SAEnum(UserTier, name="user_tier", values_callable=_enum_values), default=UserTier.FREE,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # API integrations
    twitch_user_id: Mapped[str | None] = mapped_column(String(64), index=True)

    # Quotas
    jobs_used_this_month: Mapped[int] = mapped_column(Integer, default=0)
    minutes_processed_this_month: Mapped[float] = mapped_column(Float, default=0.0)

    # Per-user webhook overrides (SaaS / power users)
    webhook_url: Mapped[str | None] = mapped_column(String(512))
    webhook_secret: Mapped[str | None] = mapped_column(String(255))

    # Channel style learning — optional weight nudges per profile
    style_weights: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    jobs: Mapped[list["Job"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    templates: Mapped[list["JobTemplate"]] = relationship(
        back_populates="user", cascade="all, delete-orphan",
    )
    platform_connections: Mapped[list["PlatformConnection"]] = relationship(
        back_populates="user", cascade="all, delete-orphan",
    )
    vault_clips: Mapped[list["VaultClip"]] = relationship(
        back_populates="user", cascade="all, delete-orphan",
    )


class LocalDevice(Base, IDMixin, TimestampMixin):
    __tablename__ = "local_devices"

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    claimed_by_user_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="SET NULL"), index=True,
    )

    jobs: Mapped[list["Job"]] = relationship(back_populates="device")


class InstallLicense(Base, IDMixin, TimestampMixin):
    """A license key's lifecycle: issued by commerce → activated on a machine.

    Rows are created by the Lemon Squeezy webhook (status="issued",
    machine_id/entitlement_jwt empty) and bound to a machine at activation
    (status="activated"). Revoked keys keep their row so re-activation fails.
    """

    __tablename__ = "install_licenses"

    license_key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    machine_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    tier: Mapped[UserTier] = mapped_column(
        SAEnum(UserTier, name="user_tier", values_callable=_enum_values),
        default=UserTier.PRO,
    )
    entitlement_jwt: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    status: Mapped[str] = mapped_column(String(16), default="issued", server_default="issued")
    order_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    customer_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    activation_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class Job(Base, IDMixin, TimestampMixin):
    __tablename__ = "jobs"

    owner_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True,
    )
    owner: Mapped["User | None"] = relationship(back_populates="jobs")
    device_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("local_devices.id", ondelete="SET NULL"), index=True,
    )
    device: Mapped["LocalDevice | None"] = relationship(back_populates="jobs")

    # Source
    source_url: Mapped[str | None] = mapped_column(Text)
    source_storage_key: Mapped[str | None] = mapped_column(String(512))  # if uploaded
    source_title: Mapped[str | None] = mapped_column(String(512))
    source_duration_secs: Mapped[float | None] = mapped_column(Float)
    source_width: Mapped[int | None] = mapped_column(Integer)
    source_height: Mapped[int | None] = mapped_column(Integer)

    # Config snapshot — the exact settings used for THIS job (frozen)
    config_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Optional user asset pack for overlays
    asset_pack_id: Mapped[str | None] = mapped_column(String(32))

    # Status / progress
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, name="job_status", values_callable=_enum_values),
        default=JobStatus.QUEUED,
        index=True,
    )
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    current_stage: Mapped[str] = mapped_column(String(64), default="queued")
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)

    # Celery task ID for cancellation
    celery_task_id: Mapped[str | None] = mapped_column(String(64), index=True)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pipeline_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stage_durations_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    clips: Mapped[list["Clip"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", order_by="Clip.rank",
    )


class Clip(Base, IDMixin, TimestampMixin):
    __tablename__ = "clips"

    job_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    job: Mapped[Job] = relationship(back_populates="clips")

    # Position
    rank: Mapped[int] = mapped_column(Integer, default=0)

    # Source window (relative to source video)
    start_secs: Mapped[float] = mapped_column(Float, nullable=False)
    end_secs: Mapped[float] = mapped_column(Float, nullable=False)

    # LLM-generated metadata
    title: Mapped[str] = mapped_column(String(255), default="")
    hook: Mapped[str] = mapped_column(Text, default="")
    emotion: Mapped[str] = mapped_column(String(32), default="neutral")
    transcript_text: Mapped[str] = mapped_column(Text, default="")
    llm_reason: Mapped[str] = mapped_column(Text, default="")
    meme_keywords: Mapped[list[str]] = mapped_column(JSON, default=list)

    # Scoring breakdown
    ensemble_score: Mapped[float] = mapped_column(Float, default=0.0)
    llm_score: Mapped[float] = mapped_column(Float, default=0.0)
    audio_score: Mapped[float] = mapped_column(Float, default=0.0)
    spectral_score: Mapped[float] = mapped_column(Float, default=0.0)
    flow_score: Mapped[float] = mapped_column(Float, default=0.0)
    chat_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Storage
    raw_storage_key: Mapped[str | None] = mapped_column(String(512))
    vertical_storage_key: Mapped[str | None] = mapped_column(String(512))
    captioned_storage_key: Mapped[str | None] = mapped_column(String(512))
    final_storage_key: Mapped[str | None] = mapped_column(String(512))
    thumbnail_storage_key: Mapped[str | None] = mapped_column(String(512))

    # File metadata
    duration_secs: Mapped[float] = mapped_column(Float, default=0.0)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)

    # Status
    status: Mapped[ClipStatus] = mapped_column(
        SAEnum(ClipStatus, name="clip_status", values_callable=_enum_values),
        default=ClipStatus.PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    render_time_secs: Mapped[float] = mapped_column(Float, default=0.0)

    # Post-gen editor overrides (caption style, reframe, overlay toggle)
    render_overrides: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    kind: Mapped[str] = mapped_column(String(32), default="discovery")
    parent_clip_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    approval_status: Mapped[str] = mapped_column(String(16), default=ApprovalStatus.DRAFT.value)

    overlays: Mapped[list["ClipOverlay"]] = relationship(
        back_populates="clip", cascade="all, delete-orphan",
    )
    publish_jobs: Mapped[list["PublishJob"]] = relationship(
        back_populates="clip", cascade="all, delete-orphan",
    )


class ClipOverlay(Base, IDMixin, TimestampMixin):
    __tablename__ = "clip_overlays"

    clip_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("clips.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    clip: Mapped[Clip] = relationship(back_populates="overlays")

    asset_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("assets.id"))
    asset: Mapped["Asset | None"] = relationship()

    trigger_time_secs: Mapped[float] = mapped_column(Float, nullable=False)
    duration_secs: Mapped[float] = mapped_column(Float, nullable=False)
    position: Mapped[str] = mapped_column(String(32), default="top_right")
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0)
    matched_keyword: Mapped[str] = mapped_column(String(255), default="")


class JobTemplate(Base, IDMixin, TimestampMixin):
    __tablename__ = "job_templates"

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    user: Mapped[User] = relationship(back_populates="templates")
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ClipFeedback(Base, IDMixin, TimestampMixin):
    __tablename__ = "clip_feedback"

    clip_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("clips.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    user_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="SET NULL"),
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 = down, 5 = up


class Asset(Base, IDMixin, TimestampMixin):
    __tablename__ = "assets"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(16), nullable=False)   # "gif" | "png" | "mp4"
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    sfx_storage_key: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    default_duration_secs: Mapped[float] = mapped_column(Float, default=2.5)

    # Pre-computed embedding (cached so we don't re-embed every job)
    embedding: Mapped[list[float] | None] = mapped_column(JSON)

    owner_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="SET NULL"),
    )
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    use_count: Mapped[int] = mapped_column(Integer, default=0)


class VaultClipStatus(str, Enum):
    COPYING = "copying"
    READY = "ready"
    FAILED = "failed"


class VaultClip(Base, IDMixin, TimestampMixin):
    __tablename__ = "vault_clips"

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    user: Mapped[User] = relationship(back_populates="vault_clips")
    source_clip_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("clips.id", ondelete="SET NULL"), index=True,
    )
    source_job_id: Mapped[str | None] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255), default="")
    hook: Mapped[str] = mapped_column(Text, default="")
    duration_secs: Mapped[float] = mapped_column(Float, default=0.0)
    storage_key: Mapped[str | None] = mapped_column(String(512))
    thumb_storage_key: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(16), default=VaultClipStatus.COPYING.value)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    publish_jobs: Mapped[list["PublishJob"]] = relationship(back_populates="vault_clip")


class InstallOAuthApp(Base, TimestampMixin):
    __tablename__ = "install_oauth_apps"

    platform: Mapped[str] = mapped_column(String(32), primary_key=True)
    client_id: Mapped[str] = mapped_column(Text, default="")
    client_secret_enc: Mapped[str | None] = mapped_column(Text)
    redirect_uri: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )


class PlatformConnection(Base, IDMixin, TimestampMixin):
    __tablename__ = "platform_connections"

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    user: Mapped[User] = relationship(back_populates="platform_connections")
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    account_label: Mapped[str] = mapped_column(String(255), default="")
    access_token_enc: Mapped[str | None] = mapped_column(Text)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    publish_jobs: Mapped[list["PublishJob"]] = relationship(back_populates="connection")


class PublishJob(Base, IDMixin, TimestampMixin):
    __tablename__ = "publish_jobs"

    clip_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("clips.id", ondelete="CASCADE"), index=True, nullable=True,
    )
    clip: Mapped[Clip | None] = relationship(back_populates="publish_jobs")
    vault_clip_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("vault_clips.id", ondelete="CASCADE"), index=True, nullable=True,
    )
    vault_clip: Mapped[VaultClip | None] = relationship(back_populates="publish_jobs")
    connection_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("platform_connections.id", ondelete="SET NULL"), index=True,
    )
    connection: Mapped[PlatformConnection | None] = relationship(back_populates="publish_jobs")
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_id: Mapped[str | None] = mapped_column(String(255))
    external_url: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
