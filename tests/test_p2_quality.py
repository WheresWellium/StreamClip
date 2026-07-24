"""P2 caption timing and confidence re-run tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.caption_timing import (
    WordGroup,
    enforce_min_display_duration,
    finalize_display_groups,
    smooth_flash_cuts,
)
from core.models import Transcript, TranscriptSegment, Word
from core.transcribe_confidence import (
    find_low_confidence_windows,
    merge_refined_window,
    rebuild_transcript_from_words,
    rerun_low_confidence_segments,
)
from core.wer_estimate import estimate_wer_proxy


def _word(text: str, start: float, end: float, prob: float = 0.9) -> Word:
    return Word(text=text, start=start, end=end, probability=prob)


def test_enforce_min_display_duration_extends_multi_word_groups():
    groups = [
        WordGroup(words=[_word("a", 0.0, 0.2), _word("b", 0.2, 0.4)], text="A B", start=0.0, end=0.4),
    ]
    out = enforce_min_display_duration(groups, min_secs=1.0)
    assert out[0].end - out[0].start >= 1.0


def test_smooth_flash_cuts_extends_short_gaps():
    groups = [
        WordGroup(words=[_word("a", 0.0, 0.5)], text="A", start=0.0, end=0.5),
        WordGroup(words=[_word("b", 0.55, 1.0)], text="B", start=0.55, end=1.0),
    ]
    out = smooth_flash_cuts(groups, min_gap=0.15, pad_before=0.05)
    assert out[0].end >= 0.5


def test_finalize_display_groups_chains_heuristics():
    groups = [
        WordGroup(
            words=[_word("one", 0.0, 0.2), _word("two", 0.2, 0.35)],
            text="ONE TWO",
            start=0.0,
            end=0.35,
        ),
    ]
    out = finalize_display_groups(groups)
    assert out[0].end >= 1.0


def test_find_low_confidence_windows_merges_adjacent_spans():
    seg = TranscriptSegment(
        id=0,
        text="low high low",
        start=0.0,
        end=3.0,
        words=(
            _word("a", 0.0, 0.4, 0.1),
            _word("b", 0.5, 0.9, 0.95),
            _word("c", 1.0, 1.4, 0.05),
        ),
    )
    tx = Transcript(segments=[seg], language="en", duration=3.0, source_path=None)  # type: ignore[arg-type]
    windows = find_low_confidence_windows(tx, 0.25)
    assert len(windows) == 2


def test_merge_refined_window_replaces_span():
    seg = TranscriptSegment(
        id=0,
        text="old words",
        start=0.0,
        end=2.0,
        words=(
            _word("old", 0.0, 0.5, 0.1),
            _word("words", 0.6, 1.0, 0.9),
        ),
    )
    tx = Transcript(segments=[seg], language="en", duration=2.0, source_path=None)  # type: ignore[arg-type]
    refined = Transcript(
        segments=[
            TranscriptSegment(
                id=0,
                text="new",
                start=0.0,
                end=0.4,
                words=(_word("new", 0.0, 0.4, 0.95),),
            ),
        ],
        language="en",
        duration=0.4,
        source_path=None,  # type: ignore[arg-type]
    )
    merged = merge_refined_window(tx, 0.0, 0.55, refined)
    texts = [w.text for w in merged.segments[0].words]
    assert "new" in texts


def test_estimate_wer_proxy():
    words = [_word("a", 0.0, 0.5, 0.1), _word("b", 0.5, 1.0, 0.9)]
    tx = rebuild_transcript_from_words(words, language="en", duration=1.0, source_path=None)
    assert estimate_wer_proxy(tx, min_prob=0.25) == 0.5


def test_rerun_low_confidence_segments_disabled():
    from core.config import get_settings

    cfg = get_settings()
    cfg = cfg.model_copy(update={"whisper": cfg.whisper.model_copy(update={"confidence_rerun_enabled": False})})
    seg = TranscriptSegment(id=0, text="x", start=0.0, end=1.0, words=(_word("x", 0.0, 1.0, 0.1),))
    tx = Transcript(segments=[seg], language="en", duration=1.0, source_path=Path("v.mp4"))
    updated, count = rerun_low_confidence_segments(Path("v.mp4"), tx, cfg)
    assert count == 0
    assert updated is tx


def test_rerun_low_confidence_segments_refines_window():
    from core.config import get_settings

    cfg = get_settings()
    cfg = cfg.model_copy(
        update={
            "whisper": cfg.whisper.model_copy(
                update={"confidence_rerun_enabled": True, "confidence_rerun_max_windows": 1},
            ),
        },
    )
    seg = TranscriptSegment(id=0, text="x", start=0.0, end=2.0, words=(_word("x", 0.0, 1.0, 0.1),))
    tx = Transcript(segments=[seg], language="en", duration=2.0, source_path=Path("v.mp4"))
    refined = Transcript(
        segments=[
            TranscriptSegment(
                id=0,
                text="fixed",
                start=0.0,
                end=0.5,
                words=(_word("fixed", 0.0, 0.5, 0.95),),
            ),
        ],
        language="en",
        duration=0.5,
        source_path=Path("clip.mp4"),
    )
    with patch("core.transcribe_confidence.extract_segment"), patch(
        "core.transcribe_confidence.transcribe_clip",
        return_value=refined,
    ):
        updated, count = rerun_low_confidence_segments(Path("v.mp4"), tx, cfg)
    assert count == 1
    assert any(w.text == "fixed" for seg in updated.segments for w in seg.words)
