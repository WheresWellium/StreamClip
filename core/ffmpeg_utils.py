"""Shared FFmpeg helpers for accurate segment extraction and probing."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import structlog

from core.config import ExportConfig
from core.export_video import audio_encode_args, output_fps_args, video_encode_args

log = structlog.get_logger(__name__)


def extract_segment(
    source: Path,
    dest: Path,
    *,
    start_secs: float,
    duration_secs: float,
    export_cfg: ExportConfig,
) -> None:
    """
    Extract a clip segment with output-side seek for frame-accurate boundaries.

    Input is specified first, then ``-ss`` (output seek) so timestamps reset to zero
    and align with per-clip Whisper re-transcription.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(source),
        "-ss", str(start_secs),
        "-t", str(duration_secs),
        "-avoid_negative_ts", "make_zero",
        *video_encode_args(export_cfg),
        *audio_encode_args(export_cfg),
        *output_fps_args(export_cfg),
        str(dest),
    ]
    log.debug("ffmpeg_extract", cmd=cmd)
    subprocess.run(cmd, check=True, capture_output=True)


def probe_duration(path: Path) -> float:
    """Return media duration in seconds (0.0 on failure)."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0.0))
    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError, TypeError) as exc:
        log.warning("ffprobe_duration_failed", path=str(path), error=str(exc))
        return 0.0


def validate_output_duration(
    path: Path,
    expected_secs: float,
    *,
    tolerance_secs: float = 1.5,
) -> bool:
    """Ensure rendered output duration is within tolerance of the source window."""
    actual = probe_duration(path)
    if actual <= 0:
        return False
    delta = abs(actual - expected_secs)
    ok = delta <= tolerance_secs
    if not ok:
        log.warning(
            "output_duration_mismatch",
            path=str(path),
            expected=expected_secs,
            actual=actual,
            delta=delta,
        )
    return ok
