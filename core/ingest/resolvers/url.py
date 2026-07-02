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
from core.subtitle_import import find_subtitle_file

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
    concurrent_fragments: int,
    subs_only: bool = False,
) -> list[str]:
    cmd = ["yt-dlp", "--no-playlist"]
    if subs_only:
        cmd.extend([
            "--skip-download",
            "--write-auto-subs",
            "--sub-langs", "en",
            "--output", str(output_path.with_suffix("")),
        ])
    else:
        format_selector = (
            f"bestvideo[height<={max_height}][ext=mp4][vcodec^=avc]"
            f"+bestaudio[ext=m4a]/"
            f"bestvideo[height<={max_height}][ext=mp4]"
            f"+bestaudio/"
            f"best[height<={max_height}][ext=mp4]/"
            f"best[ext=mp4]"
        )
        cmd.extend([
            "--format", format_selector,
            "--merge-output-format", "mp4",
            "--progress",
            "--concurrent-fragments", str(concurrent_fragments),
            "--output", str(output_path),
        ])
    cmd.append(url)
    return cmd


def fetch_subtitles_for_url(url: str, cfg: Settings, *, tier: ProcessingTier) -> None:
    """Fetch auto-subs in a separate yt-dlp pass (does not block video download)."""
    ingest_cfg = cfg.ingest
    if tier != ProcessingTier.LONG or not ingest_cfg.fetch_subs_on_long:
        return
    url_hash = _url_hash(url)
    if find_subtitle_file(cfg.cache_dir, url_hash) is not None:
        return
    output_base = cfg.cache_dir / url_hash
    cmd = _build_ytdlp_cmd(
        url, output_base.with_suffix(".mp4"), max_height=720,
        concurrent_fragments=ingest_cfg.ytdlp_concurrent_fragments,
        subs_only=True,
    )
    log.info("ingest_subtitle_fetch_start", url=url)
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        log.warning(
            "ingest_subtitle_fetch_failed",
            url=url,
            code=result.returncode,
            stderr=result.stderr[-500:] if result.stderr else "",
        )


def download_url(
    url: str,
    cfg: Settings,
    *,
    tier: ProcessingTier,
    on_progress: Callable[[float], None] | None = None,
) -> tuple[VideoMeta, bool]:
    """Download via yt-dlp with URL-hash cache. Returns (meta, was_cache_hit)."""
    ingest_cfg = cfg.ingest
    url_hash = _url_hash(url)
    cached_path = cfg.cache_dir / f"{url_hash}.mp4"
    meta_path = cached_path.with_suffix(".json")

    if cached_path.exists():
        log.info("ingest_cache_hit", url=url, path=str(cached_path))
        if on_progress:
            on_progress(1.0)
        meta = probe_video(cached_path, url=url)
        if meta_path.exists():
            with open(meta_path) as fh:
                saved = json.load(fh)
            meta = VideoMeta(**{**vars(meta), "title": saved.get("title", meta.title)})
        return meta, True

    max_h = _max_height(tier, ingest_cfg)
    tmp_path = cfg.cache_dir / f"{url_hash}.tmp.mp4"
    cmd = _build_ytdlp_cmd(
        url, tmp_path,
        max_height=max_h,
        concurrent_fragments=ingest_cfg.ytdlp_concurrent_fragments,
    )

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
    return meta, False
