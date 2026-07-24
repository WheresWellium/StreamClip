"""
StreamClip — Caption word timing utilities

Collects, repairs, and groups words for burned-in captions with accurate
per-word sync relative to the rendered clip audio.
"""

from __future__ import annotations

from typing import NamedTuple

from core.models import Transcript, Word


class WordGroup(NamedTuple):
    words: list[Word]
    text: str
    start: float
    end: float


def word_overlaps_window(word: Word, window_start: float, window_end: float) -> bool:
    """True when any part of the word falls inside the clip window."""
    return word.end > window_start and word.start < window_end


def repair_word_timing(word: Word, *, min_duration: float = 0.12) -> Word:
    """Fix zero/negative durations and very low-confidence empty tokens."""
    text = word.text.strip()
    if not text:
        return word
    start = max(0.0, word.start)
    end = word.end
    if end <= start:
        end = start + min_duration
    elif end - start < min_duration:
        end = start + min_duration
    return Word(text=text, start=start, end=end, probability=word.probability)


def collect_words_for_window(
    transcript: Transcript,
    window_start: float,
    window_end: float,
    *,
    rebase_to: float = 0.0,
    min_probability: float = 0.0,
) -> list[Word]:
    """
    Gather words overlapping ``[window_start, window_end]`` and rebase times.

    When ``rebase_to`` is 0, output timestamps are relative to ``window_start``.
    """
    collected: list[Word] = []
    for seg in transcript.segments_in_range(window_start, window_end):
        for raw in seg.words:
            if raw.probability < min_probability:
                continue
            if not word_overlaps_window(raw, window_start, window_end):
                continue
            repaired = repair_word_timing(raw)
            rebased_start = max(0.0, repaired.start - window_start + rebase_to)
            rebased_end = min(
                window_end - window_start + rebase_to,
                repaired.end - window_start + rebase_to,
            )
            if rebased_end <= rebased_start:
                continue
            collected.append(
                Word(
                    text=repaired.text,
                    start=rebased_start,
                    end=rebased_end,
                    probability=repaired.probability,
                )
            )
    collected.sort(key=lambda w: w.start)
    return collected


def group_words_for_display(
    words: list[Word],
    group_size: int,
    max_chars: int,
    *,
    pause_threshold: float = 0.28,
) -> list[WordGroup]:
    """Chunk words into on-screen groups, breaking on pauses or size limits."""
    groups: list[WordGroup] = []
    buf: list[Word] = []

    for i, word in enumerate(words):
        buf.append(word)
        at_count = len(buf) >= group_size
        at_pause = (
            i + 1 < len(words)
            and words[i + 1].start - word.end > pause_threshold
        )
        at_max_chars = sum(len(w.text) for w in buf) + len(buf) - 1 > max_chars
        at_end = i == len(words) - 1

        if buf and (at_count or at_pause or at_max_chars or at_end):
            text = " ".join(w.text.upper() for w in buf).strip()
            groups.append(
                WordGroup(
                    words=list(buf),
                    text=text,
                    start=buf[0].start,
                    end=buf[-1].end,
                )
            )
            buf = []

    return groups


def enforce_min_display_duration(
    groups: list[WordGroup],
    *,
    min_secs: float = 1.0,
) -> list[WordGroup]:
    """Extend multi-word on-screen groups to a minimum cue duration."""
    out: list[WordGroup] = []
    for group in groups:
        if len(group.words) > 1 and (group.end - group.start) < min_secs:
            out.append(
                WordGroup(
                    words=group.words,
                    text=group.text,
                    start=group.start,
                    end=group.start + min_secs,
                ),
            )
        else:
            out.append(group)
    return out


def smooth_flash_cuts(
    groups: list[WordGroup],
    *,
    min_gap: float = 0.15,
    pad_before: float = 0.05,
) -> list[WordGroup]:
    """Reduce sub-frame flashes by extending group end toward the next cue."""
    if not groups:
        return groups
    out: list[WordGroup] = []
    for i, group in enumerate(groups):
        end = group.end
        if i + 1 < len(groups):
            gap = groups[i + 1].start - group.end
            if 0 < gap < min_gap:
                end = max(group.end, groups[i + 1].start - pad_before)
        out.append(
            WordGroup(
                words=group.words,
                text=group.text,
                start=group.start,
                end=end,
            ),
        )
    return out


def finalize_display_groups(groups: list[WordGroup]) -> list[WordGroup]:
    """Apply P2 caption timing heuristics after ``group_words_for_display``."""
    return enforce_min_display_duration(smooth_flash_cuts(groups))


def build_karaoke_text(words: list[Word]) -> str:
    """
    Build ASS karaoke text using \\k tags — each word highlights in sequence
  at its spoken duration.
    """
    parts: list[str] = []
    for word in words:
        duration_cs = max(1, int(round((word.end - word.start) * 100)))
        parts.append(f"{{\\k{duration_cs}}}{word.text.upper()}")
    return " ".join(parts)


def snap_time_to_words(
    start: float,
    end: float,
    transcript: Transcript,
) -> tuple[float, float]:
    """Snap clip boundaries to nearest word edges when words are available."""
    words = [w for seg in transcript.segments for w in seg.words if w.text.strip()]
    if not words:
        return start, end

    best_start = start
    for w in words:
        if w.start <= start <= w.end or (w.start > start and w.start - start < 0.6):
            best_start = w.start
            break
        if w.end <= start and start - w.end < 0.35:
            best_start = w.start

    best_end = end
    for w in reversed(words):
        if w.start <= end <= w.end or (w.end < end and end - w.end < 0.6):
            best_end = w.end
            break
        if w.start >= end and w.start - end < 0.35:
            best_end = w.end

    if best_end <= best_start:
        return start, end
    return best_start, best_end
