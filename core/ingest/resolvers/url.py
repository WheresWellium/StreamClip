"""URL download resolver — yt-dlp with tier-aware quality."""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

import structlog

from core.config import IngestConfig, Settings
from core.errors import IngestError, NoAudioStreamError
from core.ffmpeg_bins import ffmpeg_bin
from core.ingest.probe import probe_video
from core.ingest.types import ProcessingTier
from core.ingest.url_normalize import normalize_source_url
from core.models import VideoMeta
from core.subtitle_import import find_subtitle_file
from core.ytdlp_bin import ytdlp_argv

log = structlog.get_logger(__name__)

# yt-dlp / Twitch GraphQL flakes that usually succeed on retry.
_TRANSIENT_YTDLP_MARKERS = (
    "nonetype",
    "subscriptable",
    "keyerror('data')",
    "keyerror: 'data'",
    "extractor error",
    "unable to download",
    "http error 5",
    "timed out",
    "persistedquerynotfound",
)


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _max_height(tier: ProcessingTier, ingest_cfg: IngestConfig) -> int:
    if tier == ProcessingTier.SHORT:
        return ingest_cfg.short_max_height
    if tier == ProcessingTier.MEDIUM:
        return ingest_cfg.medium_max_height
    return ingest_cfg.long_max_height


def _is_hls_platform(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(
        token in host
        for token in ("twitch.tv", "kick.com", "tiktok.com")
    )


def _format_selector(max_height: int, *, hls: bool) -> str:
    # Prefer formats that include audio. Video-only downloads look successful but
    # crash faster-whisper/PyAV with IndexError ("tuple index out of range").
    # Twitch clips report acodec=unknown on progressive MP4s, so ``acodec!=none``
    # filters reject every available format — fall through to height-bounded best
    # and let probe_video / NoAudioStreamError catch true silent files.
    if hls:
        return (
            f"best[height<={max_height}]/"
            f"bestvideo[height<={max_height}]+bestaudio/"
            f"best/"
            f"bestvideo+bestaudio"
        )
    return (
        f"bestvideo[height<={max_height}][ext=mp4][vcodec^=avc]"
        f"+bestaudio[ext=m4a]/"
        f"bestvideo[height<={max_height}][ext=mp4]+bestaudio/"
        f"bestvideo[height<={max_height}]+bestaudio/"
        f"best[height<={max_height}][ext=mp4][acodec!=none]/"
        f"best[height<={max_height}]/"
        f"best[ext=mp4][acodec!=none]/"
        f"best[acodec!=none]/"
        f"best"
    )


def _reject_or_invalidate_silent_media(
    meta: VideoMeta,
    *,
    cached_path: Path,
    meta_path: Path,
    url: str,
    allow_redownload: bool,
) -> bool:
    """Return True when a silent cache entry was purged and download should retry."""
    if meta.has_audio:
        return False
    log.warning(
        "ingest_no_audio_stream",
        url=url,
        path=str(cached_path),
        allow_redownload=allow_redownload,
    )
    cached_path.unlink(missing_ok=True)
    meta_path.unlink(missing_ok=True)
    if allow_redownload:
        return True
    raise NoAudioStreamError(
        f"Downloaded media has no audio stream: {url}",
        context={"path": str(cached_path)},
    )


def _extractor_args(url: str, cfg: Settings) -> list[str]:
    host = (urlparse(url).hostname or "").lower()
    if "twitch" not in host:
        return []
    parts: list[str] = []
    if cfg.twitch_client_id:
        parts.append(f"client_id={cfg.twitch_client_id}")
    if not parts:
        return []
    return ["--extractor-args", f"twitch:{';'.join(parts)}"]


def _referer_for_url(url: str) -> list[str]:
    host = (urlparse(url).hostname or "").lower()
    if "twitch.tv" in host:
        return ["--referer", "https://www.twitch.tv/"]
    if "kick.com" in host:
        return ["--referer", "https://kick.com/"]
    return []


def _build_ytdlp_cmd(
    url: str,
    output_path: Path,
    cfg: Settings,
    *,
    max_height: int,
    concurrent_fragments: int,
    subs_only: bool = False,
) -> list[str]:
    cmd = [*ytdlp_argv(), "--no-playlist"]
    # Without this, yt-dlp cannot merge bestvideo+bestaudio and leaves a
    # video-only file — Whisper then crashes (or we reject as no_audio_stream).
    ffmpeg_path = ffmpeg_bin(cfg)
    cmd.extend(["--ffmpeg-location", ffmpeg_path])
    cmd.extend(_referer_for_url(url))
    cmd.extend(_extractor_args(url, cfg))
    if subs_only:
        cmd.extend([
            "--skip-download",
            "--write-auto-subs",
            "--sub-langs", "en",
            "--output", str(output_path.with_suffix("")),
        ])
    else:
        hls = _is_hls_platform(url)
        cmd.extend([
            "--format", _format_selector(max_height, hls=hls),
            "--merge-output-format", "mp4",
            "--progress",
            "--concurrent-fragments", str(concurrent_fragments),
            "--output", str(output_path),
        ])
    cmd.append(url)
    return cmd


def _is_transient_ytdlp_output(lines: list[str]) -> bool:
    blob = " ".join(lines).lower()
    return any(marker in blob for marker in _TRANSIENT_YTDLP_MARKERS)


def _user_message_from_ytdlp(lines: list[str], url: str) -> str:
    blob = " ".join(lines).lower()
    if any(
        phrase in blob
        for phrase in ("video unavailable", "vod has expired", "has been deleted", "not found")
    ):
        return "This video is no longer available. Check that the URL is correct and public."
    if "live stream unavailable" in blob or "permanent link" in blob:
        return (
            "This Twitch link isn't a downloadable VOD (channel page, ended live, or "
            "unpublished highlight). Open the video → Share → copy the videos/… link, "
            "or upload the file."
        )
    if "subscriber" in blob or "sub-only" in blob or "subscription" in blob:
        return (
            "This Twitch VOD requires a subscription. Use a public VOD or configure "
            "Twitch credentials for subscriber-only content."
        )
    if "private" in blob or "login" in blob or "authentication" in blob:
        return "This video is private or requires login."
    if "ip address is blocked" in blob or "your ip address is blocked" in blob:
        return (
            "This site blocked the download from your network (IP block). "
            "Try a different source URL, upload the file, or retry from another network."
        )
    if _is_hls_platform(url) and _is_transient_ytdlp_output(lines):
        return (
            "Twitch returned a temporary error while fetching the video. "
            "Please try again in a moment."
        )
    return "Could not download the source video. Check the URL and try again."


def _run_ytdlp(
    cmd: list[str],
    on_progress: Callable[[float], None] | None,
) -> tuple[int, list[str]]:
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError as exc:
        raise IngestError(
            f"yt-dlp executable not found (cmd={cmd[:2]!r})",
            user_message=(
                "Video download tool is missing from this install. "
                "Reinstall qClip or report a bug."
            ),
            context={"cmd0": cmd[0] if cmd else None},
        ) from exc
    lines: list[str] = []
    for line in process.stdout or []:
        stripped = line.strip()
        lines.append(stripped)
        if "[download]" in stripped and "%" in stripped:
            try:
                pct = float(stripped.split("%")[0].split()[-1]) / 100.0
                if on_progress:
                    on_progress(min(pct, 1.0))
            except (ValueError, IndexError):
                pass
        log.debug("ytdlp", line=stripped)
    process.wait()
    return process.returncode or 0, lines


def fetch_subtitles_for_url(url: str, cfg: Settings, *, tier: ProcessingTier) -> None:
    """Fetch auto-subs in a separate yt-dlp pass (does not block video download)."""
    ingest_cfg = cfg.ingest
    if tier != ProcessingTier.LONG or not ingest_cfg.fetch_subs_on_long:
        return
    url = normalize_source_url(url)
    url_hash = _url_hash(url)
    if find_subtitle_file(cfg.cache_dir, url_hash) is not None:
        return
    output_base = cfg.cache_dir / url_hash
    cmd = _build_ytdlp_cmd(
        url, output_base.with_suffix(".mp4"), cfg,
        max_height=720,
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
    url = normalize_source_url(url)
    ingest_cfg = cfg.ingest
    url_hash = _url_hash(url)
    cached_path = cfg.cache_dir / f"{url_hash}.mp4"
    meta_path = cached_path.with_suffix(".json")

    if cached_path.exists():
        log.info("ingest_cache_hit", url=url, path=str(cached_path))
        meta = probe_video(cached_path, url=url)
        if meta_path.exists():
            with open(meta_path, encoding="utf-8") as fh:
                saved = json.load(fh)
            meta = VideoMeta(**{**vars(meta), "title": saved.get("title", meta.title)})
        if _reject_or_invalidate_silent_media(
            meta,
            cached_path=cached_path,
            meta_path=meta_path,
            url=url,
            allow_redownload=True,
        ):
            log.info("ingest_cache_invalidated_no_audio", url=url)
        else:
            if on_progress:
                on_progress(1.0)
            return meta, True

    max_h = _max_height(tier, ingest_cfg)
    tmp_path = cfg.cache_dir / f"{url_hash}.tmp.mp4"
    cmd = _build_ytdlp_cmd(
        url, tmp_path, cfg,
        max_height=max_h,
        concurrent_fragments=ingest_cfg.ytdlp_concurrent_fragments,
    )

    log.info("ingest_download_start", url=url, tier=tier.value, max_height=max_h)
    max_retries = ingest_cfg.ytdlp_max_retries
    base_delay = ingest_cfg.ytdlp_retry_base_delay_secs
    output_lines: list[str] = []
    return_code = 1

    for attempt in range(max_retries):
        if attempt > 0:
            delay = base_delay * (2 ** (attempt - 1))
            log.warning(
                "ingest_download_retry",
                url=url,
                attempt=attempt + 1,
                max_retries=max_retries,
                delay_secs=delay,
            )
            time.sleep(delay)
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

        return_code, output_lines = _run_ytdlp(cmd, on_progress)
        if return_code == 0:
            break
        transient = _is_transient_ytdlp_output(output_lines)
        log.warning(
            "ytdlp_failed",
            url=url,
            attempt=attempt + 1,
            code=return_code,
            transient=transient,
            tail=output_lines[-8:],
        )
        if not transient:
            break

    if return_code != 0:
        raise IngestError(
            f"yt-dlp failed with code {return_code} for URL: {url}",
            user_message=_user_message_from_ytdlp(output_lines, url),
            context={"ytdlp_tail": output_lines[-12:]},
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
    _reject_or_invalidate_silent_media(
        meta,
        cached_path=cached_path,
        meta_path=meta_path,
        url=url,
        allow_redownload=False,
    )

    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump({"title": meta.title, "duration": meta.duration}, fh, ensure_ascii=False)

    log.info(
        "ingest_download_complete",
        title=meta.title,
        duration_secs=meta.duration,
        resolution=f"{meta.width}x{meta.height}",
        has_audio=meta.has_audio,
    )
    if on_progress:
        on_progress(1.0)
    return meta, False
