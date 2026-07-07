"""Merge multiple rendered clips into one vertical output."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import structlog

from core.config import Settings
from core.export_video import audio_encode_args, output_fps_args, video_encode_args
from core.ffmpeg_bins import ffmpeg_bin
from core.storage import Storage

log = structlog.get_logger(__name__)


def splice_clip_files(
    input_paths: list[Path],
    output_path: Path,
    cfg: Settings,
    *,
    transition: str = "cut",
) -> Path:
    """Concatenate local MP4 files with optional crossfade."""
    if len(input_paths) < 2:
        raise ValueError("Need at least two clips to splice")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if transition == "crossfade" and len(input_paths) == 2:
        cmd = [
            ffmpeg_bin(), "-y",
            "-i", str(input_paths[0]),
            "-i", str(input_paths[1]),
            "-filter_complex",
            "[0:v][0:a][1:v][1:a]xfade=transition=fade:duration=0.5:offset=4[v][a]",
            "-map", "[v]", "-map", "[a]",
            *video_encode_args(cfg.export),
            *audio_encode_args(cfg.export),
            *output_fps_args(cfg.export),
            str(output_path),
        ]
    else:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False, encoding="utf-8"
        ) as fh:
            for p in input_paths:
                # Forward slashes + escaped quotes: concat demuxer chokes on
                # raw Windows backslashes and apostrophes in usernames.
                posix = p.resolve().as_posix().replace("'", r"'\''")
                fh.write(f"file '{posix}'\n")
            list_path = Path(fh.name)
        cmd = [
            ffmpeg_bin(), "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(list_path),
            "-c", "copy",
            str(output_path),
        ]

    log.info("splice_start", inputs=len(input_paths), transition=transition)
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def download_clip_finals(
    storage: Storage,
    storage_keys: list[str],
    workspace: Path,
) -> list[Path]:
    """Download final clip MP4s to workspace for splicing."""
    paths: list[Path] = []
    for i, key in enumerate(storage_keys):
        dest = workspace / f"splice_src_{i:02d}.mp4"
        storage.download(key, dest)
        paths.append(dest)
    return paths
