"""Targeted low-confidence Whisper re-runs (TDD §4.4.2)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import structlog

from core.caption_timing import repair_word_timing
from core.config import Settings
from core.ffmpeg_utils import extract_segment
from core.models import Transcript, TranscriptSegment, Word
from core.transcribe import transcribe_clip

log = structlog.get_logger(__name__)


def iter_transcript_words(transcript: Transcript) -> list[Word]:
    words: list[Word] = []
    for seg in transcript.segments:
        words.extend(seg.words)
    return words


def find_low_confidence_windows(
    transcript: Transcript,
    min_prob: float,
    *,
    max_gap: float = 0.5,
    pad_secs: float = 0.15,
) -> list[tuple[float, float]]:
    """Group contiguous low-confidence words into re-transcribe windows."""
    spans: list[tuple[float, float]] = []
    for word in iter_transcript_words(transcript):
        if word.probability >= min_prob or not word.text.strip():
            continue
        if spans and word.start - spans[-1][1] <= max_gap:
            spans[-1] = (spans[-1][0], max(word.end, spans[-1][1]))
        else:
            spans.append((word.start, word.end))

    padded: list[tuple[float, float]] = []
    duration = transcript.duration
    for start, end in spans:
        ws = max(0.0, start - pad_secs)
        we = min(duration, end + pad_secs)
        if we > ws:
            padded.append((ws, we))
    return padded


def rebuild_transcript_from_words(
    words: list[Word],
    *,
    language: str,
    duration: float,
    source_path: Path | None,
    segment_gap: float = 1.0,
) -> Transcript:
    """Rebuild segment boundaries from a flat word list."""
    if not words:
        return Transcript(
            segments=(),
            language=language,
            duration=duration,
            source_path=source_path,
        )

    sorted_words = sorted(words, key=lambda w: w.start)
    segments: list[TranscriptSegment] = []
    buf: list[Word] = []
    seg_start = sorted_words[0].start

    for i, word in enumerate(sorted_words):
        buf.append(word)
        at_end = i == len(sorted_words) - 1
        gap_break = (
            not at_end
            and sorted_words[i + 1].start - word.end > segment_gap
        )
        if at_end or gap_break:
            segments.append(
                TranscriptSegment(
                    id=len(segments),
                    text=" ".join(w.text for w in buf).strip(),
                    start=seg_start,
                    end=buf[-1].end,
                    words=tuple(buf),
                ),
            )
            buf = []
            if not at_end:
                seg_start = sorted_words[i + 1].start

    return Transcript(
        segments=tuple(segments),
        language=language,
        duration=duration,
        source_path=source_path,
    )


def merge_refined_window(
    transcript: Transcript,
    window_start: float,
    window_end: float,
    refined: Transcript,
) -> Transcript:
    """Replace words in ``[window_start, window_end]`` with clip-relative refinement."""
    kept = [
        w
        for w in iter_transcript_words(transcript)
        if w.end <= window_start or w.start >= window_end
    ]
    adjusted = [
        repair_word_timing(
            Word(
                text=w.text,
                start=w.start + window_start,
                end=w.end + window_start,
                probability=w.probability,
            ),
        )
        for seg in refined.segments
        for w in seg.words
        if w.text.strip()
    ]
    merged = sorted(kept + adjusted, key=lambda w: w.start)
    return rebuild_transcript_from_words(
        merged,
        language=transcript.language,
        duration=transcript.duration,
        source_path=transcript.source_path,
    )


def rerun_low_confidence_segments(
    source_path: Path,
    transcript: Transcript,
    cfg: Settings,
) -> tuple[Transcript, int]:
    """
  Re-transcribe up to ``confidence_rerun_max_windows`` low-confidence spans.

    Returns the updated transcript and the number of windows processed.
    """
    wcfg = cfg.whisper
    if not wcfg.confidence_rerun_enabled:
        return transcript, 0

    windows = find_low_confidence_windows(transcript, wcfg.min_word_probability)
    if not windows:
        return transcript, 0

    capped = windows[: wcfg.confidence_rerun_max_windows]
    updated = transcript
    processed = 0

    for window_start, window_end in capped:
        duration = window_end - window_start
        if duration <= 0:
            continue
        with tempfile.TemporaryDirectory(prefix="sc_conf_rerun_") as tmp:
            clip_path = Path(tmp) / "segment.mp4"
            extract_segment(
                source_path,
                clip_path,
                start_secs=window_start,
                duration_secs=duration,
                export_cfg=cfg.export,
            )
            refined = transcribe_clip(clip_path, cfg)
            updated = merge_refined_window(updated, window_start, window_end, refined)
            processed += 1
            log.info(
                "confidence_rerun_window",
                start=window_start,
                end=window_end,
                refined_words=sum(len(s.words) for s in refined.segments),
            )

    return updated, processed
