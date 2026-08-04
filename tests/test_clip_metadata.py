"""Clip metadata derivation tests."""

from __future__ import annotations

from core.clip_metadata import (
    derive_clip_metadata,
    words_text_in_range,
)
from core.models import Transcript, TranscriptSegment, Word


def test_derive_from_transcript():
    text = "I'd turn into an exorcism really quick. That was insane."
    title, hook = derive_clip_metadata(text)
    assert title == "I'd turn into an exorcism really quick."
    assert hook == text


def test_derive_truncates_long_hook():
    text = " ".join(f"word{i}" for i in range(50))
    title, hook = derive_clip_metadata(text)
    assert len(hook) <= 180
    assert hook.endswith("…")
    assert len(title.split()) <= 10


def test_derive_empty():
    title, hook = derive_clip_metadata("   ")
    assert title == "Untitled clip"
    assert hook == ""


def test_derive_strips_filler_and_collapses_repeats():
    text = "yeah dude oh my god killed killed killed that's crazy"
    title, hook = derive_clip_metadata(text)
    assert not title.lower().startswith("yeah")
    assert "killed killed killed" not in hook
    assert 1 <= hook.count("killed") <= 2
    assert "god" in title.lower() or "crazy" in title.lower() or "killed" in title.lower()


def test_words_text_in_range_avoids_segment_bleed():
    words = (
        Word(text="before", start=0.0, end=1.0, probability=0.9),
        Word(text="inside", start=5.0, end=6.0, probability=0.9),
        Word(text="after", start=9.0, end=10.0, probability=0.9),
    )
    seg = TranscriptSegment(
        id=0, text="before inside after", start=0.0, end=10.0, words=words
    )
    t = Transcript(segments=[seg], language="en", duration=10.0, source_path=None)
    assert words_text_in_range(t, 4.5, 6.5) == "inside"
    # Whole-segment join still bleeds neighbors:
    assert "before" in t.text_in_range(4.5, 6.5)
