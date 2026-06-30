"""
StreamClip — Transcription Engine
Uses faster-whisper for local, GPU-accelerated speech-to-text
with word-level timestamps. Results are cached by file hash.
Gaming terminology is hot-word boosted to reduce transcription errors
("ACE", "clutch", "one-tap", etc.).
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Iterator

import structlog
from faster_whisper import WhisperModel, BatchedInferencePipeline

from core.config import Settings, WhisperConfig
from core.models import Transcript, TranscriptSegment, Word

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


def _save_transcript(transcript: Transcript, path: Path) -> None:
    data = {
        "language": transcript.language,
        "duration": transcript.duration,
        "source_path": str(transcript.source_path),
        "segments": [
            {
                "id": s.id,
                "text": s.text,
                "start": s.start,
                "end": s.end,
                "speaker": s.speaker,
                "words": [
                    {"text": w.text, "start": w.start, "end": w.end, "probability": w.probability}
                    for w in s.words
                ],
            }
            for s in transcript.segments
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def _load_transcript(path: Path) -> Transcript:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    segments = [
        TranscriptSegment(
            id=s["id"],
            text=s["text"],
            start=s["start"],
            end=s["end"],
            speaker=s.get("speaker"),
            words=tuple(
                Word(
                    text=w["text"],
                    start=w["start"],
                    end=w["end"],
                    probability=w["probability"],
                )
                for w in s.get("words", [])
            ),
        )
        for s in data["segments"]
    ]
    return Transcript(
        segments=segments,
        language=data["language"],
        duration=data["duration"],
        source_path=Path(data["source_path"]),
    )


# ─── Model loader ──────────────────────────────────────────────────────────────

_model_cache: dict[str, WhisperModel] = {}


def _get_model(cfg: WhisperConfig) -> WhisperModel:
    device = cfg.device
    if device == "auto":
        device = "cuda" if _cuda_available() else "cpu"
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


def _cuda_available() -> bool:
    try:
        import torch
        return bool(torch.cuda.is_available())
    except ImportError:
        return False


# ─── Main transcription entry point ───────────────────────────────────────────

def transcribe(
    video_path: Path,
    cfg: Settings,
    force: bool = False,
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

    segments: list[TranscriptSegment] = []
    for i, seg in enumerate(segments_iter):
        words = tuple(
            Word(
                text=w.word.strip(),
                start=w.start,
                end=w.end,
                probability=w.probability,
            )
            for w in (seg.words or [])
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


# ─── SRT / VTT export ─────────────────────────────────────────────────────────

def _fmt_ts(secs: float, separator: str = ",") -> str:
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    ms = int((secs % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{separator}{ms:03d}"


def export_srt(transcript: Transcript, out_path: Path) -> Path:
    """Export transcript as an SRT subtitle file."""
    lines: list[str] = []
    for seg in transcript.segments:
        lines.append(str(seg.id + 1))
        lines.append(f"{_fmt_ts(seg.start)} --> {_fmt_ts(seg.end)}")
        lines.append(seg.text)
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def export_word_level_json(transcript: Transcript, out_path: Path) -> Path:
    """Export every word with its timestamp — used by the caption engine."""
    data = [
        {"word": w.text, "start": w.start, "end": w.end, "confidence": w.probability}
        for seg in transcript.segments
        for w in seg.words
    ]
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return out_path
