"""
StreamClip — Configuration Management v2
Pydantic v2 settings with YAML override, env var injection, and full
production-ready sub-configs (storage, queue, db, auth, observability).
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Literal

import structlog
import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.creator_options import (
    is_valid_caption_style,
    is_valid_reframe_preset,
)

log = structlog.get_logger(__name__)

_APP_DATA_DIR_NAME = "StreamClip"


def user_data_root() -> Path:
    """Per-user writable root used when a configured dir is not writable."""
    override = os.environ.get("STREAMCLIP_DESKTOP_DATA_DIR")
    if override:
        return Path(override)
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / _APP_DATA_DIR_NAME
    return Path.home() / f".{_APP_DATA_DIR_NAME.lower()}"


def _writable_fallback_dir(field: str, target: Path) -> Path | None:
    """Relocate *target* under the per-user data root; None if already there."""
    candidate = (user_data_root() / target.name).resolve()
    try:
        if candidate == target.resolve():
            return None
    except OSError:
        return None
    return candidate


# ─── ML sub-configs ───────────────────────────────────────────────────────────

class WhisperConfig(BaseModel):
    model_size: Literal["tiny", "base", "small", "medium", "large-v2", "large-v3"] = "large-v3"
    device: Literal["auto", "cuda", "cpu", "mps"] = "auto"
    compute_type: Literal["float16", "int8_float16", "int8", "float32"] = "float16"
    language: str | None = None
    word_timestamps: bool = True
    beam_size: int = Field(5, ge=1, le=10)
    vad_filter: bool = True
    clip_vad_filter: bool = False
    min_word_probability: float = Field(0.25, ge=0.0, le=1.0)
    confidence_rerun_enabled: bool = False
    confidence_rerun_max_windows: int = Field(3, ge=1, le=10)


class LLMConfig(BaseModel):
    provider: Literal["ollama", "openai", "anthropic"] = "ollama"
    model: str = "llama3.2"
    base_url: str = "http://localhost:11434"
    api_key: str = ""
    temperature: float = Field(0.2, ge=0.0, le=1.0)
    max_retries: int = 3
    timeout_secs: int = 60
    parallel_workers: int = Field(4, ge=1, le=8)
    # Ollama only — default num_predict is too low for virality JSON + reason text.
    num_predict: int = Field(512, ge=64, le=4096)


class HighlightConfig(BaseModel):
    target_clips: int = Field(5, ge=1, le=20)
    min_clip_duration: float = Field(15.0, ge=5.0)
    max_clip_duration: float = Field(90.0, le=300.0)
    clip_padding_secs: float = 2.5
    candidate_mode: Literal["segments", "peaks", "hybrid"] = "hybrid"
    peak_merge_gap_secs: float = Field(90.0, ge=10.0, le=600.0)
    peak_min_height: float = Field(0.55, ge=0.1, le=1.0)
    score_smoothing_window_secs: int = Field(3, ge=1, le=30)
    weight_llm_virality: float = 0.40
    weight_audio_energy: float = 0.25
    weight_spectral_novelty: float = 0.15
    weight_optical_flow: float = 0.15
    weight_chat_spikes: float = 0.05

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> "HighlightConfig":
        total = (
            self.weight_llm_virality
            + self.weight_audio_energy
            + self.weight_spectral_novelty
            + self.weight_optical_flow
            + self.weight_chat_spikes
        )
        if not (0.999 < total < 1.001):
            raise ValueError(f"Signal weights must sum to 1.0, got {total:.4f}")
        return self


class ReframeConfig(BaseModel):
    preset: str = "fps_game"
    target_width: int = 1080
    target_height: int = 1920
    smooth_window_frames: int = Field(60, ge=60)
    max_pan_velocity: float = 0.04
    hud_bottom_reserve: float = 0.15
    hud_top_reserve: float = 0.08
    fallback_center_crop: bool = True

    @field_validator("preset")
    @classmethod
    def _validate_preset(cls, v: str) -> str:
        if not is_valid_reframe_preset(v):
            raise ValueError(f"Invalid reframe preset: {v}")
        return v


class CaptionConfig(BaseModel):
    style: str = "gaming_impact"
    font_size: int = Field(72, ge=24, le=120)
    max_chars_per_line: int = 42
    words_per_group: int = 3
    highlight_keywords: bool = True
    add_emoji: bool = True
    position_y_fraction: float = 0.72
    outline_width: int = 4
    shadow_depth: int = 3
    word_level_sync: bool = True
    refine_clip_transcript: bool = True
    min_word_probability: float = Field(0.25, ge=0.0, le=1.0)
    word_hold_secs: float = Field(0.06, ge=0.0, le=0.5)
    profanity_filter: bool = False
    profanity_mode: Literal["mask", "bleep", "omit"] = "mask"
    profanity_wordlist: Path | None = None

    @field_validator("style")
    @classmethod
    def _validate_style(cls, v: str) -> str:
        if not is_valid_caption_style(v):
            raise ValueError(f"Invalid caption style: {v}")
        return v


class OverlayConfig(BaseModel):
    enabled: bool = True
    assets_dir: Path = Path("assets")
    semantic_threshold: float = Field(0.55, ge=0.0, le=1.0)
    max_overlays_per_clip: int = 2
    sfx_volume_db: float = -6.0
    gif_scale_fraction: float = 0.28
    position: Literal["top_right", "top_left", "bottom_right", "bottom_left", "center"] = "top_right"
    appear_at_peak: bool = True


class ExportConfig(BaseModel):
    codec: Literal["libx264", "libx265", "h264_nvenc", "hevc_nvenc", "h264_videotoolbox"] = "libx264"
    crf: int = Field(17, ge=0, le=51)
    preset: Literal["ultrafast", "fast", "medium", "slow"] = "fast"
    fps: int = Field(60, ge=60, le=120)
    audio_bitrate: str = "256k"
    pixel_format: str = "yuv420p"


class FfmpegConfig(BaseModel):
    """Desktop bundles ffmpeg under ``bin/ffmpeg/``; server uses PATH by default."""
    bin_dir: Path | None = None
    ffmpeg_path: Path | None = None
    ffprobe_path: Path | None = None


class WebUiConfig(BaseModel):
    """Static export served by sidecar (ADR-001 §4.7)."""
    serve_static: bool = False
    static_dir: Path = Path("static/ui")


class IngestConfig(BaseModel):
    """Tier-aware download and pipeline routing for ingest."""
    short_max_height: int = Field(720, ge=360, le=1080)
    medium_max_height: int = Field(1080, ge=480, le=1440)
    long_max_height: int = Field(1080, ge=720, le=2160)
    fetch_subs_on_long: bool = False
    defer_source_upload: bool = True
    ytdlp_concurrent_fragments: int = Field(4, ge=1, le=16)
    ytdlp_max_retries: int = Field(4, ge=1, le=8)
    ytdlp_retry_base_delay_secs: float = Field(2.0, ge=0.5, le=30.0)
    short_skip_optical_flow: bool = True
    medium_skip_optical_flow: bool = False
    short_min_clip_duration: float = Field(5.0, ge=3.0)


class FeaturesConfig(BaseModel):
    """Feature gates for SKU-tiered capabilities."""
    audio_ingest: bool = True  # v2 SKU: audio-to-clip (podcast/VO sources)


# ─── Infrastructure sub-configs ──────────────────────────────────────────────

class StorageConfig(BaseModel):
    backend: Literal["local", "s3", "minio"] = "local"
    local_root: Path = Path("workspace/storage")
    public_base_url: str = ""
    bucket: str = "streamclip"
    endpoint_url: str | None = None
    access_key: str = ""
    secret_key: str = ""
    region: str = "us-east-1"
    presigned_expiry_secs: int = 3600
    max_upload_bytes: int = Field(5 * 1024 ** 3, ge=1, description="Max direct upload size (5 GiB default)")


class RedisConfig(BaseModel):
    url: str = "redis://localhost:6379/0"
    pubsub_channel_prefix: str = "streamclip:job:"
    publish_pubsub_channel_prefix: str = "streamclip:publish:"
    progress_ttl_secs: int = 3600
    max_connections: int = 50


class DatabaseConfig(BaseModel):
    url: str = "postgresql+asyncpg://streamclip:streamclip@localhost:5432/streamclip"
    sync_url: str = "postgresql+psycopg://streamclip:streamclip@localhost:5432/streamclip"
    echo: bool = False
    pool_size: int = 20
    max_overflow: int = 10
    pool_pre_ping: bool = True

    @property
    def is_sqlite(self) -> bool:
        return self.url.startswith("sqlite") or self.sync_url.startswith("sqlite")


class CeleryConfig(BaseModel):
    broker_url: str = "redis://localhost:6379/1"
    result_backend: str = "redis://localhost:6379/2"
    task_serializer: str = "json"
    accept_content: list[str] = ["json"]
    timezone: str = "UTC"
    enable_utc: bool = True
    task_acks_late: bool = True
    task_reject_on_worker_lost: bool = True
    worker_prefetch_multiplier: int = 1
    task_time_limit: int = 3600
    task_soft_time_limit: int = 3300
    result_expires: int = 86400
    worker_max_tasks_per_child: int = 50


class QueueConfig(BaseModel):
    """Task execution backend — server uses Celery; desktop .exe uses inprocess (ADR-001)."""
    backend: Literal["celery", "inprocess"] = "celery"
    gpu_workers: int = Field(1, ge=1, le=2, description="In-process GPU slot count (desktop)")
    default_workers: int = Field(2, ge=1, le=8, description="In-process CPU/IO pool size")
    inprocess_beat: bool = Field(
        True,
        description="Run periodic (Beat) tasks in-process — scheduled publishes, cleanup (desktop)",
    )


# Known placeholders / example values that must never ship outside development.
_WEAK_AUTH_SECRET_EXACT = frozenset(
    {
        "",
        "CHANGE_ME_IN_PRODUCTION",
        "change-me-use-openssl-rand-hex-32",
        "change-me-in-production-use-openssl-rand",
        "change-me-in-production",
        "secret",
        "changeme",
    }
)
# Minimum length for a production JWT secret (openssl rand -hex 16 → 32 chars).
AUTH_SECRET_MIN_LENGTH = 32


def auth_secret_weak_reason(secret_key: str) -> str | None:
    """Return a non-secret reason if *secret_key* is unsafe for JWT signing."""
    key = (secret_key or "").strip()
    if not key:
        return "missing"
    lowered = key.lower()
    if key in _WEAK_AUTH_SECRET_EXACT or lowered in _WEAK_AUTH_SECRET_EXACT:
        return "placeholder"
    # Catch variants like "change-me-..." / "CHANGE_ME_..." from examples.
    if "change_me" in lowered or "change-me" in lowered or "changeme" in lowered:
        return "placeholder"
    if len(key) < AUTH_SECRET_MIN_LENGTH:
        return "too_short"
    return None


def is_weak_auth_secret(secret_key: str) -> bool:
    """Return True if *secret_key* is empty, a known placeholder, or too short.

    Used by Settings validation to fail closed outside development and by
    startup logging to warn local developers without exposing the secret.
    """
    return auth_secret_weak_reason(secret_key) is not None


class AuthConfig(BaseModel):
    secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    refresh_token_expire_days: int = 30
    session_refresh_token_expire_hours: int = 24
    password_reset_expire_minutes: int = 60
    allow_anonymous: bool = True
    device_scoped_anonymous: bool = True


class OnboardingConfig(BaseModel):
    sample_url: str = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    enabled: bool = True


class LicensingConfig(BaseModel):
    enabled: bool = True
    license_file: Path = Path("workspace/.streamclip-license.json")
    offline_grace_days: int = Field(7, ge=1, le=30)
    max_activations: int = Field(3, ge=1, le=10)
    # 0 = perpetual entitlement (one-time purchase); >0 = subscription days
    entitlement_days: int = Field(0, ge=0, le=36500)


class CommerceConfig(BaseModel):
    lemon_squeezy_api_key: str = ""
    lemon_squeezy_webhook_secret: str = ""
    # Phase 0 beta Lead Magnet variant → ADMIN tier on activate/webhook.
    lemon_squeezy_beta_variant_id: str = ""
    # Paid one-time Pro SKU variant.
    lemon_squeezy_pro_variant_id: str = ""
    # Base checkout URL for invite emails (no query params).
    lemon_squeezy_checkout_url: str = ""
    # Comma-separated Lemon Squeezy variant IDs that unlock audio_ingest for the buyer.
    audio_ingest_variant_ids: str = ""


class DistributionConfig(BaseModel):
    mode: Literal["byo", "managed"] = "byo"
    token_encryption_key: str = ""
    web_origin: str = "http://localhost:3000"
    youtube_publish_enabled: bool = True
    tiktok_publish_enabled: bool = False
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""


class JobRetentionConfig(BaseModel):
    enabled: bool = True
    retention_days: int = Field(7, ge=1, le=365)
    batch_size: int = Field(100, ge=1, le=500)


class CORSConfig(BaseModel):
    allow_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    allow_methods: list[str] = ["*"]
    allow_headers: list[str] = ["*"]
    allow_credentials: bool = True


class RateLimitConfig(BaseModel):
    enabled: bool = True
    requests_per_minute: int = 60
    jobs_per_hour: int = 20
    burst: int = 10
    # Dedicated, tighter ceiling for unauthenticated auth endpoints
    # (login / register / forgot-password) to blunt brute-force + email bombing.
    auth_per_minute: int = 10


class ObservabilityConfig(BaseModel):
    sentry_dsn: str = ""
    otel_endpoint: str = ""
    enable_metrics: bool = True
    # If set, the /metrics endpoint requires this value as a Bearer token or
    # X-Metrics-Key header. In development with no key set, loopback-only access
    # is enforced when environment != "development". Set via
    # STREAMCLIP_OBSERVABILITY__METRICS_API_KEY.
    metrics_api_key: str = ""


class WebhookConfig(BaseModel):
    enabled: bool = False
    url: str = ""
    secret: str = ""
    timeout_secs: int = Field(10, ge=1, le=120)
    max_retries: int = Field(3, ge=1, le=10)


# ─── Root settings ────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="STREAMCLIP_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    workspace_dir: Path = Path("workspace")
    output_dir: Path = Path("output")
    cache_dir: Path = Path(".cache")

    environment: Literal["development", "staging", "production"] = "development"

    whisper: WhisperConfig = WhisperConfig()
    llm: LLMConfig = LLMConfig()
    highlight: HighlightConfig = HighlightConfig()
    reframe: ReframeConfig = ReframeConfig()
    caption: CaptionConfig = CaptionConfig()
    overlay: OverlayConfig = OverlayConfig()
    export: ExportConfig = ExportConfig()
    ffmpeg: FfmpegConfig = FfmpegConfig()
    web: WebUiConfig = WebUiConfig()
    ingest: IngestConfig = IngestConfig()
    features: FeaturesConfig = FeaturesConfig()

    storage: StorageConfig = StorageConfig()
    redis: RedisConfig = RedisConfig()
    database: DatabaseConfig = DatabaseConfig()
    celery: CeleryConfig = CeleryConfig()
    queue: QueueConfig = QueueConfig()
    auth: AuthConfig = AuthConfig()
    onboarding: OnboardingConfig = OnboardingConfig()
    licensing: LicensingConfig = LicensingConfig()
    commerce: CommerceConfig = CommerceConfig()
    distribution: DistributionConfig = DistributionConfig()
    job_retention: JobRetentionConfig = JobRetentionConfig()
    cors: CORSConfig = CORSConfig()
    rate_limit: RateLimitConfig = RateLimitConfig()
    observability: ObservabilityConfig = ObservabilityConfig()
    webhooks: WebhookConfig = WebhookConfig()

    twitch_client_id: str = ""
    twitch_client_secret: str = ""

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_json: bool = False

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Settings":
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return cls(**data)

    @model_validator(mode="after")
    def _reject_weak_auth_secret_outside_development(self) -> "Settings":
        reason = auth_secret_weak_reason(self.auth.secret_key)
        if self.environment != "development" and reason is not None:
            length = len((self.auth.secret_key or "").strip())
            raise ValueError(
                "STREAMCLIP_AUTH__SECRET_KEY must be set to a strong random value "
                f"in {self.environment} (reason={reason}, length={length}, "
                f"min_length={AUTH_SECRET_MIN_LENGTH}). Generate one with: "
                "openssl rand -hex 32"
            )
        return self

    def _writable_slots(self) -> list[tuple[str, Path, bool, Callable[[Path], None]]]:
        """Single source of truth for every runtime path that must be writable.

        Each slot is ``(label, path, is_file, rebind)``. Anything listed here is
        automatically (a) created/relocated by :meth:`ensure_dirs` when the OS
        refuses the configured location, (b) probed by :meth:`verify_writable`,
        and (c) enforced by ``tests/test_config.py``.

        This registry exists so we never again ship a writable path that
        resolves under a read-only install prefix (e.g. ``C:\\Program Files``) —
        the root cause of both the white-screen crash and the license 500.
        Add new writable paths here, not with ad-hoc ``setdefault`` calls.
        """
        return [
            ("workspace_dir", self.workspace_dir, False,
             lambda p: setattr(self, "workspace_dir", p)),
            ("output_dir", self.output_dir, False,
             lambda p: setattr(self, "output_dir", p)),
            ("cache_dir", self.cache_dir, False,
             lambda p: setattr(self, "cache_dir", p)),
            ("storage.local_root", self.storage.local_root, False,
             lambda p: setattr(self.storage, "local_root", p)),
            ("licensing.license_file", self.licensing.license_file, True,
             lambda p: setattr(self.licensing, "license_file", p)),
        ]

    @staticmethod
    def _make_dir_writable(label: str, directory: Path) -> Path:
        """Create *directory*, relocating under the per-user data root when the
        OS refuses it. Returns the directory that actually exists and is usable.
        """
        try:
            directory.mkdir(parents=True, exist_ok=True)
            return directory
        except OSError as exc:
            fallback = _writable_fallback_dir(label, directory)
            if fallback is None:
                raise
            try:
                fallback.mkdir(parents=True, exist_ok=True)
            except OSError:
                raise exc from None
            log.warning(
                "runtime_dir_relocated",
                label=label,
                attempted=str(directory),
                fallback=str(fallback),
            )
            return fallback

    def ensure_dirs(self) -> None:
        """Create writable runtime dirs, relocating any that the OS refuses.

        Packaged desktop installs can land in a read-only prefix (e.g.
        ``C:\\Program Files``); a relative dir would otherwise raise
        PermissionError at import time and take the whole sidecar down.
        Iterates :meth:`_writable_slots` so every writable path is covered.
        """
        for label, target, is_file, rebind in self._writable_slots():
            directory = target.parent if is_file else target
            final = self._make_dir_writable(label, directory)
            if final == directory:
                continue
            rebind(final / target.name if is_file else final)

    def verify_writable(self) -> list[str]:
        """Probe every writable slot with a real write and return failures.

        Fail-fast helper for desktop startup: a clear, aggregated error beats a
        random 500 on the first job or license activation. Returns a list of
        human-readable failure strings (empty when everything is writable).
        """
        failures: list[str] = []
        for label, target, is_file, _rebind in self._writable_slots():
            directory = target.parent if is_file else target
            probe = directory / ".qclip-write-probe"
            try:
                directory.mkdir(parents=True, exist_ok=True)
                probe.write_text("ok", encoding="utf-8")
                probe.unlink()
            except OSError as exc:
                failures.append(f"{label} -> {directory} ({exc})")
        return failures


_settings: Settings | None = None


def get_settings(yaml_path: str | Path | None = None, *, reload: bool = False) -> Settings:
    """Load settings from YAML; STREAMCLIP_* env vars override file values."""
    global _settings
    if _settings is None or reload:
        env_cfg = Settings()
        cfg_file = yaml_path or os.environ.get("STREAMCLIP_CONFIG", "config.yaml")
        if Path(str(cfg_file)).exists():
            with open(cfg_file, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            file_cfg = Settings.model_validate(data)
            _settings = Settings.model_validate({
                **file_cfg.model_dump(),
                **env_cfg.model_dump(exclude_unset=True),
            })
        else:
            _settings = env_cfg
        _settings.ensure_dirs()
    return _settings
