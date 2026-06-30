"""
StreamClip — Ingest Module
Downloads or ingests a video from a URL or local path.
Handles: Twitch VODs, YouTube, Kick, local files.
Features: hash-based cache, metadata probe, progress streaming.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

import structlog

from core.config import Settings
from core.models import VideoMeta

log = structlog.get_logger(__name__)


# ─── Metadata probe ────────────────────────────────────────────────────────────

def probe_video(path: Path) -> VideoMeta:
    """
    Use ffprobe to extract complete video metadata without touching the file.
    Returns a fully populated VideoMeta dataclass.
    """
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

    # Parse fractional frame rate (e.g. "60000/1001")
    fps_raw = video_stream.get("r_frame_rate", "30/1")
    try:
        num, den = fps_raw.split("/")
        fps = float(num) / float(den)
    except (ValueError, ZeroDivisionError):
        fps = 30.0

    return VideoMeta(
        path=path,
        url=None,
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


# ─── URL → cache-key hash ─────────────────────────────────────────────────────

def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _file_hash(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


# ─── Download ─────────────────────────────────────────────────────────────────

def _build_ytdlp_cmd(
    url: str,
    output_path: Path,
    max_quality_height: int = 1080,
) -> list[str]:
    """
    Build a yt-dlp command that:
    - Prefers H.264 video (hardware-compatible everywhere)
    - Caps at max_quality_height to avoid 4K overhead
    - Merges into a single MP4
    - Downloads subtitles/chat for Twitch VODs if available
    """
    format_selector = (
        f"bestvideo[height<={max_quality_height}][ext=mp4][vcodec^=avc]"
        f"+bestaudio[ext=m4a]/"
        f"bestvideo[height<={max_quality_height}][ext=mp4]"
        f"+bestaudio/"
        f"best[ext=mp4]"
    )
    return [
        "yt-dlp",
        "--format", format_selector,
        "--merge-output-format", "mp4",
        "--write-info-json",           # save metadata sidecar
        "--write-auto-subs",           # grab auto-captions if they exist
        "--sub-langs", "en",
        "--no-playlist",
        "--progress",
        "--output", str(output_path),
        url,
    ]


def download(
    url: str,
    cfg: Settings,
    on_progress: Callable[[float], None] | None = None,
) -> VideoMeta:
    """
    Download a video from any yt-dlp–supported URL.
    Uses a SHA-256 hash of the URL as a cache key — if the file already
    exists in cfg.cache_dir, skip the download entirely.

    Args:
        url:          Any Twitch VOD, YouTube, Kick, or direct URL.
        cfg:          Global settings.
        on_progress:  Optional callback receiving fraction complete [0,1].

    Returns:
        VideoMeta for the downloaded file.
    """
    url_hash = _url_hash(url)
    cached_path = cfg.cache_dir / f"{url_hash}.mp4"
    meta_path = cached_path.with_suffix(".json")

    # ── Cache hit ──────────────────────────────────────────────────────────
    if cached_path.exists() and meta_path.exists():
        log.info("cache_hit", url=url, path=str(cached_path))
        with open(meta_path) as fh:
            saved = json.load(fh)
        meta = probe_video(cached_path)
        meta = VideoMeta(**{**vars(meta), "url": url, "title": saved.get("title", meta.title)})
        return meta

    # ── Download ───────────────────────────────────────────────────────────
    log.info("downloading", url=url)
    tmp_path = cfg.cache_dir / f"{url_hash}.tmp.mp4"
    cmd = _build_ytdlp_cmd(url, tmp_path)

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    for line in process.stdout or []:
        line = line.strip()
        # Parse yt-dlp progress lines like "[download]  42.3% of 1.20GiB"
        if "[download]" in line and "%" in line:
            try:
                pct = float(line.split("%")[0].split()[-1]) / 100.0
                if on_progress:
                    on_progress(min(pct, 1.0))
            except (ValueError, IndexError):
                pass
        log.debug("ytdlp", line=line)

    process.wait()
    if process.returncode != 0:
        from core.errors import IngestError
        raise IngestError(
            f"yt-dlp failed with code {process.returncode} for URL: {url}",
            user_message="Could not download the source video. Check the URL and try again.",
        )

    if not tmp_path.exists():
        # yt-dlp sometimes auto-names; find the most recent mp4
        candidates = sorted(cfg.cache_dir.glob(f"{url_hash}*.mp4"), key=lambda p: p.stat().st_mtime)
        if not candidates:
            raise FileNotFoundError(f"No output file found after downloading {url}")
        tmp_path = candidates[-1]

    tmp_path.rename(cached_path)

    # Probe and cache metadata
    meta = probe_video(cached_path)
    meta = VideoMeta(**{**vars(meta), "url": url})

    with open(meta_path, "w") as fh:
        json.dump({"title": meta.title, "duration": meta.duration}, fh)

    log.info(
        "download_complete",
        title=meta.title,
        duration_secs=meta.duration,
        resolution=f"{meta.width}x{meta.height}",
        fps=meta.fps,
    )
    if on_progress:
        on_progress(1.0)

    return meta


# ─── Local file ingestion ──────────────────────────────────────────────────────

def ingest_local(path: str | Path, cfg: Settings) -> VideoMeta:
    """
    Ingest a local video file. Copies it into the workspace if needed.
    Returns VideoMeta after probing.
    """
    src = Path(path).resolve()
    if not src.exists():
        raise FileNotFoundError(f"Local video not found: {src}")

    fhash = _file_hash(src)
    workspace_path = cfg.workspace_dir / f"{fhash}_{src.name}"

    if not workspace_path.exists():
        log.info("copying_to_workspace", src=str(src), dst=str(workspace_path))
        import shutil
        shutil.copy2(src, workspace_path)

    meta = probe_video(workspace_path)
    log.info(
        "ingested_local",
        title=meta.title,
        duration_secs=meta.duration,
        resolution=f"{meta.width}x{meta.height}",
    )
    return meta


# ─── Unified entry point ───────────────────────────────────────────────────────

def ingest(
    source: str | Path,
    cfg: Settings,
    on_progress: Callable[[float], None] | None = None,
) -> VideoMeta:
    """
    Unified ingest: accepts a URL string or a local file path.
    Returns VideoMeta regardless of source.
    """
    s = str(source)
    if s.startswith(("http://", "https://", "twitch.tv", "www.")):
        return download(s, cfg, on_progress=on_progress)
    return ingest_local(source, cfg)
