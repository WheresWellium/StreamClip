"""Highlight detection — guaranteed clip fallback tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.config import HighlightConfig, Settings
from core.highlights import _guaranteed_clips, find_highlights
from core.models import Transcript, TranscriptSegment, Word


def _seg(seg_id: int, text: str, start: float, end: float) -> TranscriptSegment:
    words = tuple(
        Word(text=w, start=start, end=end, probability=0.9)
        for w in text.split()
    )
    return TranscriptSegment(id=seg_id, text=text, start=start, end=end, words=words)


def _transcript(segments: list[TranscriptSegment], duration: float) -> Transcript:
    return Transcript(
        segments=segments,
        language="en",
        duration=duration,
        source_path=Path("source.mp4"),
    )


def test_guaranteed_clips_splits_short_video():
    hcfg = HighlightConfig(target_clips=3, min_clip_duration=15.0, max_clip_duration=90.0)
    transcript = _transcript([], duration=45.0)

    clips = _guaranteed_clips(transcript, hcfg)

    assert len(clips) == 1
    assert clips[0].start == 0.0
    assert clips[0].end == 45.0


def test_guaranteed_clips_multiple_chunks_for_longer_source():
    hcfg = HighlightConfig(target_clips=3, min_clip_duration=15.0, max_clip_duration=90.0)
    transcript = _transcript([], duration=180.0)

    clips = _guaranteed_clips(transcript, hcfg)

    assert len(clips) >= 2
    assert clips[0].start == 0.0
    assert clips[-1].end == pytest.approx(180.0)


def test_find_highlights_falls_back_when_scoring_yields_nothing(monkeypatch, tmp_path):
    cfg = Settings()
    video = tmp_path / "source.mp4"
    video.write_bytes(b"\x00")

    transcript = _transcript(
        [_seg(0, "hello world", 0.0, 8.0)],
        duration=30.0,
    )

    mock_scorer = MagicMock()
    mock_scorer.score_segment.return_value = None
    monkeypatch.setattr(
        "core.highlights.EnsembleScorer",
        lambda *args, **kwargs: mock_scorer,
    )

    # Force empty scored path — score_segment returning None won't append
    # because we changed to always append; mock returns None still?
    # Actually we always append now - need different test

    # Patch score_segment on instance - EnsembleScorer returns mock, but
    # find_highlights calls score_segment which we need to not add candidates.
    # Simpler: pass empty segments and rely on guaranteed fallback.

    empty_transcript = _transcript([], duration=25.0)
    clips = find_highlights(empty_transcript, video, cfg)

    assert len(clips) >= 1
    assert clips[0].end == 25.0


def test_find_highlights_includes_all_discovery_segments(monkeypatch, tmp_path):
    cfg = Settings()
    video = tmp_path / "source.mp4"
    video.write_bytes(b"\x00")

    transcript = _transcript(
        [_seg(0, "this is a quiet moment in the stream", 0.0, 20.0)],
        duration=20.0,
    )

    from core.highlights import ClipCandidate, Emotion, SignalScores

    mock_scorer = MagicMock()

    def _low_score(seg, idx):
        scores = SignalScores(llm_virality=10.0)
        scores.set_ensemble(0.1)
        return ClipCandidate(
            segment_id=seg.id,
            start=seg.start,
            end=seg.end,
            text=seg.text,
            scores=scores,
            emotion=Emotion.NEUTRAL,
        )

    mock_scorer.score_segment.side_effect = _low_score
    monkeypatch.setattr(
        "core.highlights.EnsembleScorer",
        lambda *args, **kwargs: mock_scorer,
    )

    clips = find_highlights(transcript, video, cfg)

    assert len(clips) >= 1
