"""
Phase 4 — Audio-to-clip ingest support.

Audio sources (podcasts, voiceovers) are converted into a canonical
``source.mp4`` by rendering the audio under a branded static slate at the
target vertical resolution. Downstream stages (Whisper → highlights →
process_clip) then run unchanged, with optical flow skipped since slate
frames carry no motion signal.

The slate is a static gradient (single effective frame) so the encode is
cheap even for hours-long audio — no waveform per-frame rendering on the
ingest path (performance-first).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import structlog

from core.config import Settings
from core.ffmpeg_bins import ffmpeg_bin
from core.models import VideoMeta

log = structlog.get_logger(__name__)

# Slate palette: deep navy → steel blue, matching the app theme
_SLATE_GRADIENT = "gradients=s={w}x{h}:c0=0x0B1220:c1=0x1E3A5F:n=2:speed=0.0001"
_SLATE_FPS = 30


def is_audio_only(meta: VideoMeta) -> bool:
    """True when the source has usable audio but no real video stream."""
    return meta.has_audio and (meta.width <= 0 or meta.height <= 0)


def render_audio_slate(
    audio_path: Path,
    output_path: Path,
    cfg: Settings,
) -> Path:
    """
    Mux audio under a static branded slate video at the reframe target size.

    Uses libx264 with stillimage tuning regardless of the export codec —
    this runs on the CPU ingest worker and must not require NVENC.
    """
    width = cfg.reframe.target_width
    height = cfg.reframe.target_height
    gradient = _SLATE_GRADIENT.format(w=width, h=height)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_bin(), "-y",
        "-f", "lavfi", "-i", gradient,
        "-i", str(audio_path),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
        "-crf", "28",
        "-r", str(_SLATE_FPS),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", cfg.export.audio_bitrate,
        "-shortest",
        str(output_path),
    ]
    log.info("rendering_audio_slate", audio=str(audio_path), size=f"{width}x{height}")
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path
