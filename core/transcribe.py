"""
StreamClip — Transcription Engine
Uses faster-whisper for local, GPU-accelerated speech-to-text
with word-level timestamps. Results are cached by file hash.
Gaming terminology is hot-word boosted to reduce transcription errors
("ACE", "clutch", "one-tap", etc.).
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

import structlog
from faster_whisper import WhisperModel

from core.caption_timing import repair_word_timing
from core.config import Settings, WhisperConfig
from core.models import Transcript, TranscriptSegment, Word
from core.storage import Storage, job_key, make_storage
from core.transcript_io import load_transcript, save_transcript

log = structlog.get_logger(__name__)

# ─── Gaming vocabulary hot-words ──────────────────────────────────────────────
# faster-whisper supports hot-word boosting to improve domain-specific accuracy.
GAMING_HOTWORDS: list[str] = [
    "clutch", "ace", "one-tap", "headshot", "no-scope", "teamwipe",
    "rotation", "respawn", "ulti", "ult", "engage", "flank", "peek",
    "push", "rotate", "defuse", "plant", "streamer", "VOD", "Twitch",
    "TikTok", "subscribe", "clip that", "let's go", "holy", "insane",
    "W", "L", "GG", "GGWP", "POG", "pog", "copium", "malding",
    "cringe", "based", "lowkey", "no cap",
]


# ─── Cache utilities ───────────────────────────────────────────────────────────

def _video_hash(path: Path, sample_bytes: int = 2 << 20) -> str:
    """SHA-256 over the first 2 MB + last 2 MB + file size — fast for large files."""
    h = hashlib.sha256()
    size = path.stat().st_size
    h.update(str(size).encode())
    with open(path, "rb") as fh:
        h.update(fh.read(sample_bytes))
        if size > sample_bytes * 2:
            fh.seek(-sample_bytes, 2)
            h.update(fh.read(sample_bytes))
    return h.hexdigest()[:20]


def _cache_path(video_path: Path, cache_dir: Path, model_size: str) -> Path:
    vhash = _video_hash(video_path)
    return cache_dir / f"transcript_{vhash}_{model_size}.json"


# JSON persistence shared with API-side consumers (no whisper dependency there).
_save_transcript = save_transcript
_load_transcript = load_transcript


def save_transcript_json(transcript: Transcript, out_path: Path) -> Path:
    """Persist full transcript (segments + words) for job storage and reuse."""
    _save_transcript(transcript, out_path)
    return out_path


def load_job_transcript(
    job_id: str,
    cfg: Settings,
    *,
    storage: Storage | None = None,
    source_path: Path | None = None,
    fallback_transcribe: bool = True,
) -> Transcript:
    """
    Load a persisted job transcript from workspace or object storage.

    Falls back to transcribing ``source_path`` when no blob exists (CLI / recovery),
    unless ``fallback_transcribe`` is False — then a missing blob raises.
    """
    from core.ingest.service import get_job_source_path

    workspace = cfg.workspace_dir / "jobs" / job_id
    local_json = workspace / "transcript.json"
    store: Storage = storage or make_storage(cfg)
    key = job_key(job_id, "transcript", "transcript.json")

    if not local_json.exists() and store.exists(key):
        store.download(key, local_json)

    if local_json.exists():
        return _load_transcript(local_json)

    if not fallback_transcribe:
        raise FileNotFoundError(f"No persisted transcript for job {job_id}")

    if source_path is None:
        source_path = get_job_source_path(cfg, job_id)

    if not source_path.exists():
        raise FileNotFoundError(
            f"No transcript or source video for job {job_id}",
        )

    return transcribe(source_path, cfg)


# ─── Model loader ──────────────────────────────────────────────────────────────

_model_cache: dict[str, WhisperModel] = {}


def _get_model(cfg: WhisperConfig) -> WhisperModel:
    from core.config import get_settings
    from core.gpu_profile import effective_whisper_device

    device = effective_whisper_device(get_settings())
    compute_type = cfg.compute_type
    if device == "cpu" and compute_type in ("float16", "int8_float16"):
        compute_type = "int8"
    key = f"{cfg.model_size}:{device}:{compute_type}"
    if key not in _model_cache:
        log.info(
            "loading_whisper_model",
            model=cfg.model_size,
            device=device,
            compute_type=compute_type,
        )
        t0 = time.perf_counter()
        _model_cache[key] = WhisperModel(
            cfg.model_size,
            device=device,
            compute_type=compute_type,
        )
        log.info("model_loaded", elapsed_secs=f"{time.perf_counter() - t0:.1f}")
    return _model_cache[key]


# ─── Main transcription entry point ───────────────────────────────────────────

def transcribe(
    video_path: Path,
    cfg: Settings,
    force: bool = False,
    subtitle_path: Path | None = None,
) -> Transcript:
    """
    Transcribe a video file with word-level timestamps.
    Results are cached; set force=True to re-transcribe.

    Args:
        video_path:  Path to the source MP4 / WAV.
        cfg:         Global settings.
        force:       Ignore existing cache and re-run.

    Returns:
        A fully populated Transcript with per-word timestamps.
    """
    wcfg = cfg.whisper
    cache_file = _cache_path(video_path, cfg.cache_dir, wcfg.model_size)

    # ── Cache hit ──────────────────────────────────────────────────────────
    if cache_file.exists() and not force:
        log.info("transcript_cache_hit", path=str(cache_file))
        return _load_transcript(cache_file)

    # ── Subtitle seed from yt-dlp ──────────────────────────────────────────
    if subtitle_path and subtitle_path.exists() and not force:
        from core.subtitle_import import parse_srt

        parsed = parse_srt(subtitle_path)
        if parsed and len(parsed.segments) >= 3:
            log.info("transcript_subtitle_seed", path=str(subtitle_path))
            from dataclasses import replace
            transcript = replace(parsed, source_path=video_path)
            _save_transcript(transcript, cache_file)
            return transcript

    # ── Transcribe ─────────────────────────────────────────────────────────
    model = _get_model(wcfg)
    log.info("transcribing", video=str(video_path), model=wcfg.model_size)
    t0 = time.perf_counter()

    segments_iter, info = model.transcribe(
        str(video_path),
        language=wcfg.language,
        word_timestamps=wcfg.word_timestamps,
        beam_size=wcfg.beam_size,
        vad_filter=wcfg.vad_filter,
        # Gaming hot-word boosting (reduces hallucination on domain vocab)
        hotwords=", ".join(GAMING_HOTWORDS),
        # Suppress common hallucinations in silent / music sections
        suppress_tokens=[-1],
        condition_on_previous_text=True,
    )

    segments = _parse_segments(segments_iter, wcfg)

    elapsed = time.perf_counter() - t0
    log.info(
        "transcription_complete",
        language=info.language,
        duration_secs=info.duration,
        num_segments=len(segments),
        rtf=f"{elapsed / max(info.duration, 1):.3f}",  # real-time factor
        elapsed_secs=f"{elapsed:.1f}",
    )

    transcript = Transcript(
        segments=segments,
        language=info.language,
        duration=info.duration,
        source_path=video_path,
    )

    # ── Persist cache ──────────────────────────────────────────────────────
    _save_transcript(transcript, cache_file)
    return transcript


def _parse_segments(
    segments_iter,
    _wcfg: WhisperConfig,
) -> list[TranscriptSegment]:
    """Build segments with repaired word timings from a faster-whisper iterator."""
    segments: list[TranscriptSegment] = []
    for i, seg in enumerate(segments_iter):
        words = tuple(
            repair_word_timing(
                Word(
                    text=w.word.strip(),
                    start=w.start,
                    end=w.end,
                    probability=w.probability,
                ),
            )
            for w in (seg.words or [])
            if w.word.strip()
        )
        segments.append(
            TranscriptSegment(
                id=i,
                text=seg.text.strip(),
                start=seg.start,
                end=seg.end,
                words=words,
            )
        )
    return segments


def transcribe_clip(video_path: Path, cfg: Settings) -> Transcript:
    """
    Re-transcribe a short extracted clip for caption sync.

    Timestamps are relative to the clip file (0-based). VAD is disabled by
    default so short gaming reactions are not stripped.
    """
    wcfg = cfg.whisper
    model = _get_model(wcfg)
    log.info("transcribing_clip", video=str(video_path))

    segments_iter, info = model.transcribe(
        str(video_path),
        language=wcfg.language,
        word_timestamps=True,
        beam_size=wcfg.beam_size,
        vad_filter=wcfg.clip_vad_filter,
        hotwords=", ".join(GAMING_HOTWORDS),
        suppress_tokens=[-1],
        condition_on_previous_text=False,
    )
    segments = _parse_segments(segments_iter, wcfg)
    return Transcript(
        segments=segments,
        language=info.language,
        duration=info.duration,
        source_path=video_path,
    )
