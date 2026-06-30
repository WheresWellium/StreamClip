"""URL download resolver — yt-dlp with tier-aware quality."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable
from pathlib import Path

import structlog

from core.config import IngestConfig, Settings
from core.errors import IngestError
from core.ingest.probe import probe_video
from core.ingest.types import ProcessingTier
from core.models import VideoMeta

log = structlog.get_logger(__name__)


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _max_height(tier: ProcessingTier, ingest_cfg: IngestConfig) -> int:
    if tier == ProcessingTier.SHORT:
        return ingest_cfg.short_max_height
    if tier == ProcessingTier.MEDIUM:
        return ingest_cfg.medium_max_height
    return ingest_cfg.long_max_height


def _build_ytdlp_cmd(
    url: str,
    output_path: Path,
    *,
    max_height: int,
    fetch_subs: bool,
) -> list[str]:
    format_selector = (
        f"bestvideo[height<={max_height}][ext=mp4][vcodec^=avc]"
        f"+bestaudio[ext=m4a]/"
        f"bestvideo[height<={max_height}][ext=mp4]"
        f"+bestaudio/"
        f"best[height<={max_height}][ext=mp4]/"
        f"best[ext=mp4]"
    )
    cmd = [
        "yt-dlp",
        "--format", format_selector,
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--progress",
        "--output", str(output_path),
    ]
    if fetch_subs:
        cmd.extend(["--write-auto-subs", "--sub-langs", "en"])
    cmd.append(url)
    return cmd


def download_url(
    url: str,
    cfg: Settings,
    *,
    tier: ProcessingTier,
    on_progress: Callable[[float], None] | None = None,
) -> VideoMeta:
    """Download via yt-dlp with URL-hash cache."""
    ingest_cfg = cfg.ingest
    url_hash = _url_hash(url)
    cached_path = cfg.cache_dir / f"{url_hash}.mp4"
    meta_path = cached_path.with_suffix(".json")

    if cached_path.exists():
        log.info("ingest_cache_hit", url=url, path=str(cached_path))
        meta = probe_video(cached_path, url=url)
        if meta_path.exists():
            with open(meta_path) as fh:
                saved = json.load(fh)
            meta = VideoMeta(**{**vars(meta), "title": saved.get("title", meta.title)})
        return meta

    max_h = _max_height(tier, ingest_cfg)
    fetch_subs = tier == ProcessingTier.LONG and ingest_cfg.fetch_subs_on_long
    tmp_path = cfg.cache_dir / f"{url_hash}.tmp.mp4"
    cmd = _build_ytdlp_cmd(url, tmp_path, max_height=max_h, fetch_subs=fetch_subs)

    log.info("ingest_download_start", url=url, tier=tier.value, max_height=max_h)
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    for line in process.stdout or []:
        line = line.strip()
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
        raise IngestError(
            f"yt-dlp failed with code {process.returncode} for URL: {url}",
            user_message="Could not download the source video. Check the URL and try again.",
        )

    if not tmp_path.exists():
        candidates = sorted(
            cfg.cache_dir.glob(f"{url_hash}*.mp4"),
            key=lambda p: p.stat().st_mtime,
        )
        if not candidates:
            raise IngestError(
                f"No output file after downloading {url}",
                user_message="Download completed but no video file was produced.",
            )
        tmp_path = candidates[-1]

    tmp_path.rename(cached_path)
    meta = probe_video(cached_path, url=url)

    with open(meta_path, "w") as fh:
        json.dump({"title": meta.title, "duration": meta.duration}, fh)

    log.info(
        "ingest_download_complete",
        title=meta.title,
        duration_secs=meta.duration,
        resolution=f"{meta.width}x{meta.height}",
    )
    if on_progress:
        on_progress(1.0)
    return meta
