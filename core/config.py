"""
StreamClip — Configuration Management v2
Pydantic v2 settings with YAML override, env var injection, and full
production-ready sub-configs (storage, queue, db, auth, observability).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ─── ML sub-configs ───────────────────────────────────────────────────────────

class WhisperConfig(BaseModel):
    model_size: Literal["tiny", "base", "small", "medium", "large-v2", "large-v3"] = "large-v3"
    device: Literal["auto", "cuda", "cpu", "mps"] = "auto"
    compute_type: Literal["float16", "int8_float16", "int8", "float32"] = "float16"
    language: str | None = None
    word_timestamps: bool = True
    beam_size: int = Field(5, ge=1, le=10)
    vad_filter: bool = True


class LLMConfig(BaseModel):
    provider: Literal["ollama", "openai", "anthropic"] = "ollama"
    model: str = "llama3.2"
    base_url: str = "http://localhost:11434"
    api_key: str = ""
    temperature: float = Field(0.2, ge=0.0, le=1.0)
    max_retries: int = 3
    timeout_secs: int = 60


class HighlightConfig(BaseModel):
    target_clips: int = Field(5, ge=1, le=20)
    min_clip_duration: float = Field(15.0, ge=5.0)
    max_clip_duration: float = Field(90.0, le=300.0)
    clip_padding_secs: float = 2.5
    min_virality_score: int = Field(55, ge=0, le=100)
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
    preset: Literal["fps_game", "moba", "battle_royale", "irl", "podcast", "auto"] = "fps_game"
    target_width: int = 1080
    target_height: int = 1920
    smooth_window_frames: int = 45
    max_pan_velocity: float = 0.04
    hud_bottom_reserve: float = 0.15
    hud_top_reserve: float = 0.08
    fallback_center_crop: bool = True


class CaptionConfig(BaseModel):
    style: Literal["gaming_impact", "minimal_white", "tiktok_pop", "podcast_clean"] = "gaming_impact"
    font_size: int = Field(72, ge=24, le=120)
    max_chars_per_line: int = 25
    words_per_group: int = 3
    highlight_keywords: bool = True
    add_emoji: bool = True
    position_y_fraction: float = 0.72
    outline_width: int = 4
    shadow_depth: int = 3


class OverlayConfig(BaseModel):
    assets_dir: Path = Path("assets")
    semantic_threshold: float = Field(0.55, ge=0.0, le=1.0)
    max_overlays_per_clip: int = 2
    sfx_volume_db: float = -6.0
    gif_scale_fraction: float = 0.28
    position: Literal["top_right", "top_left", "bottom_right", "bottom_left", "center"] = "top_right"
    appear_at_peak: bool = True


class ExportConfig(BaseModel):
    codec: Literal["libx264", "libx265", "h264_nvenc", "hevc_nvenc"] = "h264_nvenc"
    crf: int = Field(17, ge=0, le=51)
    preset: Literal["ultrafast", "fast", "medium", "slow"] = "fast"
    fps: int = 60
    audio_bitrate: str = "256k"
    pixel_format: str = "yuv420p"
    two_pass: bool = False


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


class RedisConfig(BaseModel):
    url: str = "redis://localhost:6379/0"
    pubsub_channel_prefix: str = "streamclip:job:"
    progress_ttl_secs: int = 3600
    max_connections: int = 50


class DatabaseConfig(BaseModel):
    url: str = "postgresql+asyncpg://streamclip:streamclip@localhost:5432/streamclip"
    sync_url: str = "postgresql+psycopg://streamclip:streamclip@localhost:5432/streamclip"
    echo: bool = False
    pool_size: int = 20
    max_overflow: int = 10
    pool_pre_ping: bool = True


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


class AuthConfig(BaseModel):
    secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    refresh_token_expire_days: int = 30
    allow_anonymous: bool = True


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


class ObservabilityConfig(BaseModel):
    sentry_dsn: str = ""
    otel_endpoint: str = ""
    enable_metrics: bool = True
    metrics_port: int = 9090


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

    storage: StorageConfig = StorageConfig()
    redis: RedisConfig = RedisConfig()
    database: DatabaseConfig = DatabaseConfig()
    celery: CeleryConfig = CeleryConfig()
    auth: AuthConfig = AuthConfig()
    cors: CORSConfig = CORSConfig()
    rate_limit: RateLimitConfig = RateLimitConfig()
    observability: ObservabilityConfig = ObservabilityConfig()

    twitch_client_id: str = ""
    twitch_client_secret: str = ""

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_json: bool = False

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Settings":
        with open(path) as fh:
            data = yaml.safe_load(fh) or {}
        return cls(**data)

    def ensure_dirs(self) -> None:
        for d in (self.workspace_dir, self.output_dir, self.cache_dir):
            d.mkdir(parents=True, exist_ok=True)


_settings: Settings | None = None


def get_settings(yaml_path: str | Path | None = None, *, reload: bool = False) -> Settings:
    """Load settings from YAML; STREAMCLIP_* env vars override file values."""
    global _settings
    if _settings is None or reload:
        env_cfg = Settings()
        cfg_file = yaml_path or os.environ.get("STREAMCLIP_CONFIG", "config.yaml")
        if Path(str(cfg_file)).exists():
            with open(cfg_file) as fh:
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
