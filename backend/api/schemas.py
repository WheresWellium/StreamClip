"""
StreamClip — API Schemas (Pydantic v2)

Wire-format models. Separate from ORM models so we control exactly what
goes out the door (no leaking internal columns, no accidental N+1 loads).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from core.creator_options import (
    is_valid_caption_style,
    is_valid_content_profile,
    is_valid_reframe_preset,
)


# ─── Job ─────────────────────────────────────────────────────────────────────

class CreateJobRequest(BaseModel):
    """Body for POST /api/jobs"""
    source_url: str | None = Field(
        None,
        description="A Twitch VOD, YouTube, Kick, or direct video URL.",
    )
    source_upload_key: str | None = Field(
        None,
        description="Storage key from a prior upload (use /api/uploads/init first).",
    )
    target_clips: int = Field(5, ge=1, le=20)
    caption_style: str = "gaming_impact"
    reframe_preset: str = "fps_game"
    content_profile: str = "gaming"
    asset_pack_id: str | None = Field(None, description="User asset pack for overlays")

    @field_validator("caption_style")
    @classmethod
    def _validate_caption_style(cls, v: str) -> str:
        if not is_valid_caption_style(v):
            raise ValueError(f"Invalid caption_style: {v}")
        return v

    @field_validator("reframe_preset")
    @classmethod
    def _validate_reframe_preset(cls, v: str) -> str:
        if not is_valid_reframe_preset(v):
            raise ValueError(f"Invalid reframe_preset: {v}")
        return v

    @field_validator("content_profile")
    @classmethod
    def _validate_content_profile(cls, v: str) -> str:
        if not is_valid_content_profile(v):
            raise ValueError(f"Invalid content_profile: {v}")
        return v

    @field_validator("source_url")
    @classmethod
    def _validate_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.startswith(("http://", "https://")):
            raise ValueError("source_url must start with http:// or https://")
        return v


class JobError(BaseModel):
    code: str
    message: str


class ClipOverlayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    trigger_time_secs: float
    duration_secs: float
    position: str
    similarity_score: float
    matched_keyword: str


class ClipPublishStatusOut(BaseModel):
    platform: str
    status: str
    publish_job_id: str
    external_url: str | None = None


class ClipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rank: int
    title: str
    hook: str
    emotion: str
    start_secs: float
    end_secs: float
    duration_secs: float
    ensemble_score: float
    llm_score: float
    audio_score: float
    spectral_score: float
    flow_score: float
    chat_score: float = 0.0
    status: str
    error_message: str | None = None
    render_time_secs: float
    file_size_bytes: int
    transcript_text: str = ""
    llm_reason: str = ""
    meme_keywords: list[str] = []
    overlays: list[ClipOverlayOut] = []
    kind: str = "discovery"
    parent_clip_ids: list[str] = []
    render_overrides: dict[str, object] = {}
    approval_status: str = "draft"

    # Presigned URLs filled in by service layer
    download_url: str | None = None
    thumbnail_url: str | None = None
    publish_statuses: list[ClipPublishStatusOut] = Field(default_factory=list)


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_url: str | None
    source_title: str | None
    source_duration_secs: float | None
    status: str
    progress: float
    current_stage: str
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    pipeline_started_at: datetime | None = None
    finished_at: datetime | None = None
    stage_durations_json: dict[str, float] | None = None
    content_profile: str | None = None
    clips: list[ClipOut] = []


class JobListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_title: str | None
    source_duration_secs: float | None
    status: str
    progress: float
    created_at: datetime
    clip_count: int = 0


class JobListResponse(BaseModel):
    jobs: list[JobListItem]
    total: int
    limit: int
    offset: int


class RegenerateClipResponse(BaseModel):
    clip_id: str
    job_id: str
    status: str = "queued"


# ─── Uploads ─────────────────────────────────────────────────────────────────

class UploadInitRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field("video/mp4", max_length=64)
    size_bytes: int | None = Field(None, ge=1)


class UploadInitResponse(BaseModel):
    upload_id: str
    upload_url: str           # presigned PUT
    storage_key: str          # opaque to client, used when creating job
    expires_in: int           # seconds


# ─── Health / Meta ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str | None = Field(None, max_length=120)


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str | None
    tier: str
    jobs_used_this_month: int
    minutes_processed_this_month: float


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class ClaimDeviceRequest(BaseModel):
    device_id: str | None = Field(None, min_length=8, max_length=64)


class ClaimDeviceResponse(BaseModel):
    device_id: str
    jobs_claimed: int


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str
    redis: bool
    database: bool
    storage: bool
    ollama: bool | None = None


class StackHealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    checks: dict[str, bool]
    worker: bool | None = None
    beat: bool | None = None
    web: bool | None = None


# ─── Progress events (SSE payload) ───────────────────────────────────────────

class ProgressEvent(BaseModel):
    job_id: str
    stage: str
    progress: float
    message: str = ""
    status: Literal["processing", "done", "error"] = "processing"
    ts: float
    stage_elapsed_secs: float | None = None
    total_elapsed_secs: float | None = None
    eta_secs: float | None = None
    stage_durations: dict[str, float] | None = None


# ─── Templates ────────────────────────────────────────────────────────────────

class JobTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    config_json: dict[str, object]


class CreateJobTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    config_json: dict[str, object] = Field(default_factory=dict)


# ─── Clip editor ─────────────────────────────────────────────────────────────

class UpdateClipRequest(BaseModel):
    start_secs: float | None = Field(None, ge=0)
    end_secs: float | None = Field(None, gt=0)
    title: str | None = Field(None, min_length=1, max_length=200)
    hook: str | None = Field(None, max_length=500)
    caption_style: str | None = None
    reframe_preset: str | None = None
    overlay_enabled: bool | None = None
    rerender: bool = True

    @field_validator("caption_style")
    @classmethod
    def _validate_caption_style(cls, v: str | None) -> str | None:
        if v is not None and not is_valid_caption_style(v):
            raise ValueError(f"Invalid caption_style: {v}")
        return v

    @field_validator("reframe_preset")
    @classmethod
    def _validate_reframe_preset(cls, v: str | None) -> str | None:
        if v is not None and not is_valid_reframe_preset(v):
            raise ValueError(f"Invalid reframe_preset: {v}")
        return v


# ─── Batch jobs ──────────────────────────────────────────────────────────────

class BatchCreateJobRequest(BaseModel):
    jobs: list[CreateJobRequest] = Field(..., min_length=1, max_length=20)


class BatchCreateJobResponse(BaseModel):
    jobs: list[JobOut]


# ─── Splice ──────────────────────────────────────────────────────────────────

class SpliceClipsRequest(BaseModel):
    clip_ids: list[str] = Field(..., min_length=2, max_length=10)
    transition: Literal["cut", "crossfade"] = "cut"


class SpliceClipsResponse(BaseModel):
    clip_id: str
    job_id: str
    status: str = "queued"


# ─── Assets vault ────────────────────────────────────────────────────────────

class CreateAssetRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    asset_type: Literal["gif", "png", "mp4"]
    storage_key: str
    sfx_storage_key: str | None = None
    description: str = Field(..., min_length=3)
    tags: list[str] = Field(default_factory=list)
    default_duration_secs: float = Field(2.5, gt=0, le=30)


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    asset_type: str
    storage_key: str
    sfx_storage_key: str | None
    description: str
    tags: list[str]
    default_duration_secs: float
    is_public: bool
    use_count: int


# ─── Webhooks (per-user) ─────────────────────────────────────────────────────

class WebhookSettingsRequest(BaseModel):
    webhook_url: str | None = None
    webhook_secret: str | None = None


class WebhookSettingsOut(BaseModel):
    webhook_url: str | None
    configured: bool


# ─── Clip feedback / style learning ───────────────────────────────────────────

class ClipFeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)


class ClipFeedbackOut(BaseModel):
    clip_id: str
    rating: int


# ─── Social distribution (publish / schedule) ────────────────────────────────

class PublishClipRequest(BaseModel):
    platform: Literal["youtube_shorts", "tiktok"]
    title: str | None = None
    description: str | None = None


class PublishClipResponse(BaseModel):
    clip_id: str
    platform: str
    status: str
    message: str
    publish_job_id: str | None = None


class PublishNowRequest(BaseModel):
    clip_id: str | None = None
    vault_clip_id: str | None = None
    platform: Literal["youtube_shorts", "tiktok"]
    title: str | None = None
    description: str | None = None
    scheduled_at: datetime | None = None
    idempotency_key: str | None = Field(default=None, max_length=64)


# ─── Onboarding ───────────────────────────────────────────────────────────────

class OnboardingCompleteRequest(BaseModel):
    device_id: str


class OnboardingCompleteResponse(BaseModel):
    device_id: str
    onboarding_complete: bool = True


# ─── License ──────────────────────────────────────────────────────────────────

class LicenseActivateRequest(BaseModel):
    license_key: str = Field(..., min_length=16)
    machine_id: str = Field(..., min_length=8, max_length=128)


class LicenseStatusOut(BaseModel):
    active: bool
    tier: str
    expires_at: datetime | None = None
    machine_id: str | None = None


class LicenseActivateResponse(BaseModel):
    tier: str
    expires_at: datetime | None
    entitlement_jwt: str


# ─── Stack health ─────────────────────────────────────────────────────────────

class StackHealthOut(BaseModel):
    postgres: Literal["ok", "down"]
    redis: Literal["ok", "down"]
    minio: Literal["ok", "down"]
    worker: Literal["ok", "degraded", "down", "skipped"]
    ollama: Literal["ok", "down", "skipped"]
    whisper_device: Literal["cpu", "cuda", "mps", "unknown"]


# ─── Clip approval ─────────────────────────────────────────────────────────────

class ClipApprovalRequest(BaseModel):
    approval_status: Literal["draft", "approved", "rejected"]


class ClipApprovalResponse(BaseModel):
    clip_id: str
    approval_status: str


# ─── Clip Vault ────────────────────────────────────────────────────────────────

class SaveVaultClipRequest(BaseModel):
    clip_id: str
    title: str | None = None


class VaultClipOut(BaseModel):
    id: str
    title: str
    hook: str
    duration_secs: float
    status: str
    source_clip_id: str | None
    source_job_id: str | None
    saved_at: datetime
    metadata_json: dict[str, object] = Field(default_factory=dict)
    video_url: str | None = None
    thumbnail_url: str | None = None
    publish_statuses: list[ClipPublishStatusOut] = Field(default_factory=list)


class VaultQuotaOut(BaseModel):
    used: int
    limit: int


# ─── Distribution ─────────────────────────────────────────────────────────────

class PlatformConnectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    platform: str
    account_label: str
    is_active: bool


class OAuthAppOut(BaseModel):
    platform: str
    client_id: str
    redirect_uri: str
    configured: bool


class OAuthAppUpdateRequest(BaseModel):
    client_id: str = Field(..., min_length=4)
    client_secret: str = Field(..., min_length=4)
    redirect_uri: str | None = None


class OAuthStartResponse(BaseModel):
    auth_url: str
    platform: str


class SchedulePublishRequest(BaseModel):
    clip_id: str | None = None
    vault_clip_id: str | None = None
    platform: Literal["youtube_shorts", "tiktok"]
    scheduled_at: datetime
    title: str | None = None
    description: str | None = None


class PublishJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    clip_id: str | None
    vault_clip_id: str | None = None
    platform: str
    status: str
    scheduled_at: datetime | None
    published_at: datetime | None = None
    external_id: str | None
    external_url: str | None = None
    title: str = ""
    error_message: str | None = None
    last_error_code: str | None = None
    created_at: datetime | None = None


class BatchPublishClipsRequest(BaseModel):
    platform: Literal["youtube_shorts", "tiktok"]
    clip_ids: list[str] | None = None
    title: str | None = None
    description: str | None = None


class BatchPublishClipsResponse(BaseModel):
    jobs: list[PublishJobOut]
    skipped: int = 0
