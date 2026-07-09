"""
StreamClip — Exception Hierarchy

A single root exception (`StreamClipError`) lets callers catch every domain
error with one except clause. Specific subclasses preserve the failure
category so retries and user-facing messages can be precise.

Design rules:
  • Every exception carries a `code` (machine-readable) and a `user_message`
    (safe to surface in the UI).
  • The original cause (if any) is attached via `__cause__` — never swallow it.
  • Retryable errors expose `is_retryable=True` so Celery decides via taxonomy,
    not by string-matching on .args[0].
"""

from __future__ import annotations

import re
from typing import Any

_INTERNAL_DETAIL_RE = re.compile(
    r"(traceback|file \"|ytdlp|ffmpeg|\.py:|\\|[A-Z]:\\|Exception:|Error:)",
    re.IGNORECASE,
)


def expose_error_context() -> bool:
    """Return True when API responses may include diagnostic ``context`` payloads."""
    from core.config import get_settings

    return get_settings().environment == "development"


def sanitize_user_message(
    message: str | None,
    *,
    fallback: str = "Something went wrong.",
) -> str:
    """Strip strings that look like stack traces or tool output before UI display."""
    if not message or not str(message).strip():
        return fallback
    text = str(message).strip()
    if len(text) > 280 or _INTERNAL_DETAIL_RE.search(text):
        return fallback
    return text


def clip_failure_message(exc: BaseException) -> str:
    """User-safe clip error text for DB + SSE (never raw ``str(exc)``)."""
    if isinstance(exc, StreamClipError):
        return exc.user_message
    return "Video processing failed."


def publish_failure_message(exc: BaseException) -> str:
    """User-safe publish error text for DB + SSE."""
    if isinstance(exc, StreamClipError):
        return exc.user_message
    return "Publish failed. Try again or check your platform connection."


class StreamClipError(Exception):
    """Root of every StreamClip domain error."""

    code: str = "streamclip_error"
    is_retryable: bool = False
    user_message: str = "Something went wrong."
    http_status: int = 500

    def __init__(
        self,
        message: str | None = None,
        *,
        user_message: str | None = None,
        code: str | None = None,
        http_status: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message or self.user_message)
        self.context: dict[str, Any] = context or {}
        if user_message is not None:
            self.user_message = user_message
        # Per-instance overrides for one-off errors that don't warrant a subclass
        if code is not None:
            self.code = code
        if http_status is not None:
            self.http_status = http_status

    def to_dict(self) -> dict[str, Any]:
        """Serialisable payload for API responses and structured logs."""
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.user_message,
            "retryable": self.is_retryable,
        }
        if expose_error_context() and self.context:
            payload["context"] = self.context
        return payload


# ─── Ingest ──────────────────────────────────────────────────────────────────

class IngestError(StreamClipError):
    code = "ingest_failed"
    user_message = "Could not download the source video."
    http_status = 400


class InvalidSourceError(IngestError):
    code = "invalid_source"
    user_message = "That URL or file isn't supported."
    http_status = 400


class DownloadTimeoutError(IngestError):
    code = "download_timeout"
    user_message = "The download took too long."
    is_retryable = True
    http_status = 504


class UnsupportedMediaError(IngestError):
    code = "unsupported_media"
    user_message = "We couldn't read this media file."
    http_status = 415


# ─── Transcription ───────────────────────────────────────────────────────────

class TranscriptionError(StreamClipError):
    code = "transcription_failed"
    user_message = "Couldn't transcribe the audio."
    is_retryable = True


class NoAudioStreamError(TranscriptionError):
    code = "no_audio_stream"
    user_message = "The source video has no audio track."
    is_retryable = False
    http_status = 400


class ModelLoadError(TranscriptionError):
    code = "model_load_failed"
    user_message = "ML model failed to load on the server."
    is_retryable = False


# ─── Highlights ──────────────────────────────────────────────────────────────

class HighlightDetectionError(StreamClipError):
    code = "highlight_detection_failed"
    user_message = "Couldn't detect highlights in this video."
    is_retryable = True


class LLMUnavailableError(HighlightDetectionError):
    code = "llm_unavailable"
    user_message = "The LLM scorer is unreachable."
    is_retryable = True
    http_status = 503


class NoHighlightsFoundError(HighlightDetectionError):
    code = "no_highlights_found"
    user_message = "We didn't find any clip-worthy moments."
    is_retryable = False
    http_status = 200  # not an error to the user — just empty result


# ─── Video processing ───────────────────────────────────────────────────────

class VideoProcessingError(StreamClipError):
    code = "video_processing_failed"
    user_message = "Video processing failed."
    is_retryable = True


class FFmpegError(VideoProcessingError):
    code = "ffmpeg_failed"
    user_message = "FFmpeg encoding failed."


class ReframeError(VideoProcessingError):
    code = "reframe_failed"
    user_message = "Vertical reframing failed."


class CaptionError(VideoProcessingError):
    code = "caption_failed"
    user_message = "Caption rendering failed."


class OverlayError(VideoProcessingError):
    code = "overlay_failed"
    user_message = "Overlay compositing failed."


# ─── Infra ──────────────────────────────────────────────────────────────────

class StorageError(StreamClipError):
    code = "storage_failed"
    user_message = "Could not read or write storage."
    is_retryable = True


class JobNotFoundError(StreamClipError):
    code = "job_not_found"
    user_message = "Job not found."
    http_status = 404


class QuotaExceededError(StreamClipError):
    code = "quota_exceeded"
    user_message = "You've hit your processing quota."
    http_status = 429


class AuthError(StreamClipError):
    code = "auth_failed"
    user_message = "Authentication failed."
    http_status = 401


class DeviceIdRequiredError(StreamClipError):
    code = "device_id_required"
    user_message = "X-Device-Id header required for anonymous requests"
    http_status = 400


# ─── Licensing ──────────────────────────────────────────────────────────────

class LicenseError(StreamClipError):
    code = "license_error"
    user_message = "License operation failed."
    http_status = 400


class InvalidLicenseKeyError(LicenseError):
    code = "invalid_license_key"
    user_message = "That license key isn't valid."
    http_status = 400


class LicenseRevokedError(LicenseError):
    code = "license_revoked"
    user_message = "This license key has been revoked."
    http_status = 403


class ActivationLimitError(LicenseError):
    code = "activation_limit_reached"
    user_message = "This license key has reached its activation limit."
    http_status = 403
