"""Derive clip title and hook text from transcript/caption content."""

from __future__ import annotations

import re

_TITLE_MAX_WORDS = 10
_HOOK_MAX_CHARS = 180


def derive_clip_metadata(text: str) -> tuple[str, str]:
    """
    Build display title and hook from spoken transcript text.

    Title: first sentence (or first N words) — what appears on the card header.
    Hook: fuller quote from the clip — matches what viewers hear in captions.
    """
    cleaned = " ".join(text.split()).strip()
    if not cleaned:
        return "Untitled clip", ""

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    first_sentence = sentences[0].strip() if sentences else cleaned

    title_words = first_sentence.split()
    if len(title_words) > _TITLE_MAX_WORDS:
        title = " ".join(title_words[:_TITLE_MAX_WORDS]) + "…"
    else:
        title = first_sentence

    if len(cleaned) <= _HOOK_MAX_CHARS:
        hook = cleaned
    else:
        truncated = cleaned[: _HOOK_MAX_CHARS - 1]
        hook = truncated.rsplit(" ", 1)[0] + "…"

    return title, hook
