"""Video metadata probing — shared ffprobe wrapper."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from core.models import VideoMeta


def probe_video(path: Path, *, url: str | None = None) -> VideoMeta:
    """Extract metadata via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)

    fmt = data.get("format", {})
    streams = data.get("streams", [])

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    fps_raw = video_stream.get("r_frame_rate", "30/1")
    try:
        num, den = fps_raw.split("/")
        fps = float(num) / float(den)
    except (ValueError, ZeroDivisionError):
        fps = 30.0

    return VideoMeta(
        path=path,
        url=url,
        title=fmt.get("tags", {}).get("title", path.stem),
        duration=float(fmt.get("duration", 0)),
        width=int(video_stream.get("width", 0)),
        height=int(video_stream.get("height", 0)),
        fps=fps,
        size_bytes=int(fmt.get("size", 0)),
        has_audio=audio_stream is not None,
        video_codec=video_stream.get("codec_name", "unknown"),
        audio_codec=audio_stream.get("codec_name", "none") if audio_stream else "none",
    )
