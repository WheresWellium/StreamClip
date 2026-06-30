"""Caption timing utility tests."""

from __future__ import annotations

from core.caption_timing import (
    build_karaoke_text,
    collect_words_for_window,
    repair_word_timing,
    snap_time_to_words,
    word_overlaps_window,
)
from core.models import Transcript, TranscriptSegment, Word


def _word(text: str, start: float, end: float, prob: float = 0.9) -> Word:
    return Word(text=text, start=start, end=end, probability=prob)


def _transcript(words: list[Word]) -> Transcript:
    seg = TranscriptSegment(id=0, text=" ".join(w.text for w in words), start=words[0].start, end=words[-1].end, words=tuple(words))
    return Transcript(segments=[seg], language="en", duration=words[-1].end, source_path=None)  # type: ignore[arg-type]


def test_word_overlaps_window():
    w = _word("hi", 9.5, 10.2)
    assert word_overlaps_window(w, 10.0, 20.0)
    assert not word_overlaps_window(w, 11.0, 20.0)


def test_collect_words_includes_boundary_overlap():
    words = [_word("before", 9.0, 10.5), _word("inside", 12.0, 13.0)]
    t = _transcript(words)
    collected = collect_words_for_window(t, 10.0, 15.0)
    assert len(collected) == 2
    assert collected[0].text == "before"
    assert collected[0].start == 0.0


def test_repair_zero_duration_word():
    fixed = repair_word_timing(_word("uh", 5.0, 5.0))
    assert fixed.end > fixed.start


def test_build_karaoke_contains_k_tags():
    words = [_word("hello", 0.0, 0.5), _word("world", 0.5, 1.0)]
    text = build_karaoke_text(words)
    assert "\\k" in text
    assert "HELLO" in text


def test_snap_time_to_words():
    words = [_word("one", 10.0, 10.4), _word("two", 10.5, 11.0)]
    t = _transcript(words)
    start, end = snap_time_to_words(10.1, 10.8, t)
    assert start == 10.0
    assert end == 11.0
