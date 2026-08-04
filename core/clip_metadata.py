"""Derive clip title and hook text from transcript/caption content."""

from __future__ import annotations

import re

from core.models import Transcript

_TITLE_MAX_WORDS = 10
_HOOK_MAX_CHARS = 180

# Leading fillers that make raw ASR dumps look unfinished as titles.
_FILLER_OPENERS = frozenset(
    {
        "yeah",
        "yea",
        "uh",
        "um",
        "uhh",
        "umm",
        "like",
        "so",
        "okay",
        "ok",
        "alright",
        "well",
        "dude",
        "bro",
        "man",
        "oh",
        "ah",
        "hmm",
        "actually",
        "basically",
        "literally",
    }
)


def words_text_in_range(transcript: Transcript, start: float, end: float) -> str:
    """Join word tokens overlapping ``[start, end]`` (avoids whole-segment bleed)."""
    parts: list[str] = []
    for seg in transcript.segments_in_range(start, end):
        if seg.words:
            for w in seg.words:
                if w.end > start and w.start < end:
                    t = w.text.strip()
                    if t:
                        parts.append(t)
        else:
            # Segment-only transcripts (subtitle seed): keep segment text.
            t = seg.text.strip()
            if t:
                parts.append(t)
    return " ".join(parts)


def _collapse_repeated_tokens(text: str) -> str:
    tokens = text.split()
    if not tokens:
        return text
    out: list[str] = []
    prev_norm = ""
    streak = 0
    for tok in tokens:
        norm = re.sub(r"[^\w']+", "", tok.lower())
        if norm and norm == prev_norm:
            streak += 1
            # Keep at most two identical tokens in a row (ASR stutter), drop 3+.
            if streak >= 3:
                continue
        else:
            streak = 1
            prev_norm = norm
        out.append(tok)
    return " ".join(out)


def _strip_filler_openers(text: str) -> str:
    tokens = text.split()
    while tokens:
        head = re.sub(r"[^\w']+", "", tokens[0].lower())
        if head in _FILLER_OPENERS:
            tokens = tokens[1:]
            continue
        break
    return " ".join(tokens)


def derive_clip_metadata(text: str) -> tuple[str, str]:
    """
    Build display title and hook from spoken transcript text.

    Title: first energetic clause (filler stripped) — card header.
    Hook: fuller quote from the clip — matches what viewers hear in captions.
    """
    cleaned = _collapse_repeated_tokens(" ".join(text.split()).strip())
    if not cleaned:
        return "Untitled clip", ""

    for_title = _strip_filler_openers(cleaned) or cleaned

    # Prefer first clause separated by comma / dash / sentence end.
    clause = re.split(r"(?<=[.!?])\s+|,\s+| — | - ", for_title, maxsplit=1)[0].strip()
    if not clause:
        clause = for_title

    title_words = clause.split()
    if len(title_words) > _TITLE_MAX_WORDS:
        title = " ".join(title_words[:_TITLE_MAX_WORDS]) + "…"
    else:
        title = clause

    if len(cleaned) <= _HOOK_MAX_CHARS:
        hook = cleaned
    else:
        truncated = cleaned[: _HOOK_MAX_CHARS - 1]
        hook = truncated.rsplit(" ", 1)[0] + "…"

    return title, hook
