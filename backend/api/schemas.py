"""
StreamClip — API Schemas (Pydantic v2)

Wire-format models. Separate from ORM models so we control exactly what
goes out the door (no leaking internal columns, no accidental N+1 loads).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from core.creator_options import (
    DEFAULT_ASPECT_RATIO,
    is_valid_aspect_ratio,
    is_valid_caption_style,
    is_valid_content_profile,
    is_valid_reframe_preset,
)
from core.ingest.url_normalize import normalize_source_url
from core.support.attachments import ALLOWED_SUPPORT_ATTACHMENT_TYPES, MAX_ATTACHMENT_BYTES


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
    aspect_ratio: str = Field(
        DEFAULT_ASPECT_RATIO,
        description="Export aspect ratio (see /api/meta aspect_ratios).",
    )
    asset_pack_id: str | None = Field(None, description="User asset pack for overlays")
    display_title: str | None = Field(
        None,
        max_length=512,
        description="Optional user-facing job name (overrides ingest title in UI).",
    )
    profanity_filter: bool = Field(
        False, description="Censor profanity in captions and clip title/hook.",
    )
    profanity_mode: Literal["mask", "bleep", "omit"] = Field(
        "mask", description="How censored words render: mask (f***), bleep (•••), omit.",
    )

    @field_validator("display_title")
    @classmethod
    def _normalize_display_title(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        return stripped if stripped else None

    @field_validator("caption_style")
    @classmethod
    def _validate_caption_style(cls, v: str) -> str:
        if not is_valid_caption_style(v):
            raise ValueError(f"Invalid caption_style: {v}")
        return v

    @field_validator("aspect_ratio")
    @classmethod
    def _validate_aspect_ratio(cls, v: str) -> str:
        if not is_valid_aspect_ratio(v):
            raise ValueError(f"Invalid aspect_ratio: {v}")
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
        try:
            return normalize_source_url(v)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc


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
    approval_status: Literal["draft", "approved", "rejected"] = "draft"

    # Presigned URLs filled in by service layer
    download_url: str | None = None
    thumbnail_url: str | None = None
    publish_statuses: list[ClipPublishStatusOut] = Field(default_factory=list)


class ClipWordOut(BaseModel):
    """One caption word with clip-relative timing."""
    index: int
    text: str
    start: float
    end: float


class ClipWordsOut(BaseModel):
    """Word list used for caption rendering — basis for transcript_edits indices."""
    clip_id: str
    words: list[ClipWordOut]


class TranscriptWordOut(BaseModel):
    """Word-level timestamp from a job transcript."""
    index: int
    text: str
    start: float
    end: float
    confidence: float


class TranscriptSegmentSummaryOut(BaseModel):
    id: int
    text: str
    start: float
    end: float
    word_count: int


class TranscriptTimestampsOut(BaseModel):
    """GET /api/jobs/{job_id}/transcript/timestamps"""
    job_id: str
    language: str
    duration_secs: float
    words: list[TranscriptWordOut]
    segments: list[TranscriptSegmentSummaryOut]


class CaptionExportRequest(BaseModel):
    """POST /api/jobs/{job_id}/caption-export"""
    format: Literal["srt", "vtt", "ttml", "ass", "mp4"]
    clip_id: str | None = Field(None, max_length=32)
    style: str | None = Field(None, description="Caption style preset override")
    word_level: bool = True
    burn_in: bool = False


class CaptionExportOut(BaseModel):
    job_id: str
    format: str
    status: Literal["ready", "queued"]
    download_url: str | None = None
    expires_at: datetime | None = None


class UpdateJobRequest(BaseModel):
    """Body for PATCH /api/jobs/{id}"""
    display_title: str | None = Field(None, max_length=512)

    @field_validator("display_title")
    @classmethod
    def _normalize_display_title(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        return stripped if stripped else None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_url: str | None
    source_title: str | None
    display_title: str | None = None
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
    aspect_ratio: str | None = None
    clips: list[ClipOut] = []
    title_audit_id: str | None = None


class JobListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_title: str | None
    display_title: str | None = None
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

ALLOWED_VIDEO_UPLOAD_TYPES = (
    "video/mp4",
    "video/quicktime",
    "video/x-matroska",
    "video/webm",
)

# Phase 4 — audio-to-clip (gated by features.audio_ingest at the service layer)
ALLOWED_AUDIO_UPLOAD_TYPES = (
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/aac",
    "audio/ogg",
    "audio/flac",
)


class UploadInitRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field("video/mp4", max_length=64)
    size_bytes: int | None = Field(None, ge=1)

    @field_validator("content_type")
    @classmethod
    def _validate_content_type(cls, v: str) -> str:
        normalized = v.strip().lower()
        if normalized not in ALLOWED_VIDEO_UPLOAD_TYPES + ALLOWED_AUDIO_UPLOAD_TYPES:
            raise ValueError(f"Unsupported upload content_type: {v}")
        return normalized


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
    remember_me: bool = True


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


class UpdateProfileRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=120)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=16, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str


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
    extra: dict[str, Any] | None = None


# ─── Support / bug reports ────────────────────────────────────────────────────

BUG_REPORT_CATEGORIES = (
    "ingest",
    "transcription",
    "captions",
    "reframe",
    "overlays",
    "vault",
    "distribution",
    "license_billing",
    "performance",
    "ui",
    "other",
)


class BugReportRequest(BaseModel):
    """Body for POST /api/support/bug-reports"""
    message: str = Field(..., min_length=10, max_length=5000)
    categories: list[str] = Field(..., min_length=1, max_length=len(BUG_REPORT_CATEGORIES))
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    job_id: str | None = Field(None, max_length=32)
    attachment_ids: list[str] = Field(default_factory=list, max_length=3)
    environment: dict[str, str] | None = Field(
        None, description="Client-collected context: app version, OS, browser.",
    )

    @field_validator("categories")
    @classmethod
    def _validate_categories(cls, v: list[str]) -> list[str]:
        unknown = [c for c in v if c not in BUG_REPORT_CATEGORIES]
        if unknown:
            raise ValueError(f"Unknown categories: {unknown}")
        return list(dict.fromkeys(v))  # dedupe, keep order

    @field_validator("attachment_ids")
    @classmethod
    def _dedupe_attachment_ids(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(v))

    @field_validator("environment")
    @classmethod
    def _limit_environment(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        if v is not None and len(v) > 20:
            raise ValueError("Too many environment entries")
        return v


class BugReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    severity: str
    categories: list[str]
    created_at: datetime
    email_notification: str = "skipped_unconfigured"
    ops_notification: str = "skipped_unconfigured"


class BetaFeedbackRequest(BaseModel):
    """Body for POST /api/support/beta-feedback"""

    message: str = Field(..., min_length=10, max_length=5000)
    topic: Literal["question", "idea", "help", "praise", "other"] = "help"
    area: (
        Literal[
            "getting_started",
            "ingest",
            "clipping",
            "captions",
            "reframe",
            "vault",
            "distribution",
            "license_billing",
            "performance",
            "ui",
            "other",
        ]
        | None
    ) = None
    environment: dict[str, str] | None = None

    @field_validator("environment")
    @classmethod
    def _limit_environment(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        if v is not None and len(v) > 20:
            raise ValueError("Too many environment entries")
        return v


class BetaFeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    topic: str
    created_at: datetime
    ops_notification: str = "skipped_unconfigured"


class BugReportAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    severity: str
    categories: list[str]
    message: str
    user_id: str | None
    device_id: str | None
    job_id: str | None
    assigned_to: str | None
    environment: dict[str, Any] | None
    created_at: datetime


class BugReportAdminUpdateRequest(BaseModel):
    """Body for PATCH /api/admin/bug-reports/{id}"""

    status: Literal["open", "triage", "assigned", "resolved"] | None = None
    assigned_to: str | None = Field(None, max_length=32)
    resolution_note: str | None = Field(None, max_length=2000)


class SupportAttachmentInitRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., max_length=128)
    size_bytes: int = Field(..., ge=1)

    @field_validator("content_type")
    @classmethod
    def _validate_content_type(cls, v: str) -> str:
        normalized = v.strip().lower()
        if normalized not in ALLOWED_SUPPORT_ATTACHMENT_TYPES:
            raise ValueError(f"Unsupported attachment content_type: {v}")
        return normalized

    @field_validator("size_bytes")
    @classmethod
    def _validate_size(cls, v: int) -> int:
        if v > MAX_ATTACHMENT_BYTES:
            raise ValueError("Attachment exceeds 5 MB limit")
        return v


class SupportAttachmentInitResponse(BaseModel):
    attachment_id: str
    upload_url: str
    storage_key: str
    expires_in: int


# ─── Privacy / data contribution ──────────────────────────────────────────────

class PrivacySettingsOut(BaseModel):
    data_contribution_opt_in: bool


class PrivacySettingsRequest(BaseModel):
    data_contribution_opt_in: bool


_USER_PREF_LIST_MAX = 50
_USER_PREF_STRING_MAX = 64
_ALLOWED_TITLE_STYLES = frozenset({"tutorial", "tip", "explainer", "promo", "gaming"})


def _trim_pref_list(values: list[str] | None, *, max_items: int) -> list[str]:
    if not values:
        return []
    out: list[str] = []
    for raw in values:
        text = str(raw).strip()[:_USER_PREF_STRING_MAX]
        if text and text not in out:
            out.append(text)
        if len(out) >= max_items:
            break
    return out


class UserPreferencesOut(BaseModel):
    memory_enabled: bool = False
    vocabulary: list[str] = Field(default_factory=list)
    brand_names: list[str] = Field(default_factory=list)
    title_style: str = "gaming"
    preferred_tags: list[str] = Field(default_factory=list)
    language_hint: str = "en"
    recent_titles: list[str] = Field(default_factory=list)

    @classmethod
    def from_storage(cls, raw: dict[str, Any] | None) -> UserPreferencesOut:
        data = raw or {}
        style = str(data.get("title_style", "gaming")).strip().lower()
        if style not in _ALLOWED_TITLE_STYLES:
            style = "gaming"
        return cls(
            memory_enabled=bool(data.get("memory_enabled", False)),
            vocabulary=_trim_pref_list(data.get("vocabulary"), max_items=_USER_PREF_LIST_MAX),
            brand_names=_trim_pref_list(data.get("brand_names"), max_items=_USER_PREF_LIST_MAX),
            title_style=style,
            preferred_tags=_trim_pref_list(data.get("preferred_tags"), max_items=_USER_PREF_LIST_MAX),
            language_hint=str(data.get("language_hint", "en")).strip()[:16] or "en",
            recent_titles=_trim_pref_list(data.get("recent_titles"), max_items=10),
        )


class UserPreferencesUpdateRequest(BaseModel):
    memory_enabled: bool | None = None
    vocabulary: list[str] | None = None
    brand_names: list[str] | None = None
    title_style: Literal["tutorial", "tip", "explainer", "promo", "gaming"] | None = None
    preferred_tags: list[str] | None = None
    language_hint: str | None = Field(None, max_length=16)

    def as_patch(self) -> dict[str, Any]:
        patch: dict[str, Any] = {}
        if self.memory_enabled is not None:
            patch["memory_enabled"] = self.memory_enabled
        if self.vocabulary is not None:
            patch["vocabulary"] = _trim_pref_list(self.vocabulary, max_items=_USER_PREF_LIST_MAX)
        if self.brand_names is not None:
            patch["brand_names"] = _trim_pref_list(self.brand_names, max_items=_USER_PREF_LIST_MAX)
        if self.title_style is not None:
            patch["title_style"] = self.title_style
        if self.preferred_tags is not None:
            patch["preferred_tags"] = _trim_pref_list(
                self.preferred_tags,
                max_items=_USER_PREF_LIST_MAX,
            )
        if self.language_hint is not None:
            patch["language_hint"] = self.language_hint.strip() or "en"
        return patch


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
    aspect_ratio: str | None = None
    overlay_enabled: bool | None = None
    transcript_edits: dict[str, str] | None = Field(
        None,
        description=(
            "Word-level caption edits keyed by word index (from the clip words "
            "endpoint). Empty string removes the word. Empty dict clears all edits."
        ),
    )
    caption_words_per_group: int | None = Field(
        None, ge=1, le=8,
        description="Max words per on-screen caption line (phrase grouping).",
    )
    rerender: bool = True

    @field_validator("transcript_edits")
    @classmethod
    def _validate_transcript_edits(
        cls, v: dict[str, str] | None,
    ) -> dict[str, str] | None:
        if v is None:
            return v
        if len(v) > 500:
            raise ValueError("Too many transcript edits (max 500)")
        for key, text in v.items():
            if not key.isdigit():
                raise ValueError(f"transcript_edits keys must be word indices: {key!r}")
            if len(text) > 80:
                raise ValueError("Edited word too long (max 80 chars)")
        return v

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

    @field_validator("aspect_ratio")
    @classmethod
    def _validate_aspect_ratio(cls, v: str | None) -> str | None:
        if v is not None and not is_valid_aspect_ratio(v):
            raise ValueError(f"Invalid aspect_ratio: {v}")
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
    # End of the current verification window, not the end of the purchase.
    expires_at: datetime | None = None
    machine_id: str | None = None
    # True for one-time purchases: the licence itself never lapses.
    perpetual: bool = False
    # Set when the install had a token but the key is no longer valid.
    revoked: bool = False


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


class UpdateVaultClipRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


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


class VaultQuotaDimensionOut(BaseModel):
    used: int
    limit: int
    warning: Literal["approaching", "critical", "exceeded"] | None = None


class VaultQuotaBytesOut(VaultQuotaDimensionOut):
    used_human: str
    limit_human: str


class VaultQuotaThresholdsOut(BaseModel):
    warn_at_pct: int = 75
    critical_at_pct: int = 90


class VaultQuotaOut(BaseModel):
    clips: VaultQuotaDimensionOut
    bytes: VaultQuotaBytesOut
    tier: str
    thresholds: VaultQuotaThresholdsOut


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


class UpdatePublishJobRequest(BaseModel):
    """Edit a queued/scheduled publish before it uploads."""
    title: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    scheduled_at: datetime | None = None


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


# ─── Title suggestions (§7.1.3) ───────────────────────────────────────────────

class TitleSuggestionOut(BaseModel):
    rank: int = Field(ge=1, le=3)
    title: str = Field(max_length=80)
    confidence: float = Field(ge=0.0, le=1.0)
    hook: str


class TitleSuggestionsResponse(BaseModel):
    job_id: str
    tone: str = "gaming"
    suggestions: list[TitleSuggestionOut]
    model: str
    generated_at: datetime
