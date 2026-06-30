"""
StreamClip — API Schemas (Pydantic v2)

Wire-format models. Separate from ORM models so we control exactly what
goes out the door (no leaking internal columns, no accidental N+1 loads).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


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
    caption_style: Literal[
        "gaming_impact", "tiktok_pop", "minimal_white", "podcast_clean"
    ] = "gaming_impact"
    reframe_preset: Literal[
        "fps_game", "moba", "battle_royale", "irl", "podcast", "auto"
    ] = "fps_game"
    min_virality_score: int = Field(55, ge=0, le=100)

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
    status: str
    error_message: str | None = None
    render_time_secs: float
    file_size_bytes: int
    overlays: list[ClipOverlayOut] = []

    # Presigned URLs filled in by service layer
    download_url: str | None = None
    thumbnail_url: str | None = None


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
    finished_at: datetime | None = None
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

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str
    redis: bool
    database: bool
    storage: bool


# ─── Progress events (SSE payload) ───────────────────────────────────────────

class ProgressEvent(BaseModel):
    job_id: str
    stage: str
    progress: float
    message: str = ""
    status: Literal["processing", "done", "error"] = "processing"
    ts: float
