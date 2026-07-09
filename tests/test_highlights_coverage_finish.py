"""Finish highlights module coverage gaps (optical flow, NMS, guaranteed clips)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from core.config import get_settings
from core.highlights import (
    EnsembleScorer,
    _AudioAnalyser,
    _OpticalFlowAnalyser,
    _discover_peak_windows,
    _guaranteed_clips,
    _nms,
    _snap_boundaries,
    find_highlights,
)
from core.models import ClipCandidate, Emotion, SignalScores, Transcript, TranscriptSegment


def _transcript(duration: float = 60.0, *, segments: list[TranscriptSegment] | None = None) -> Transcript:
    segs = segments or [
        TranscriptSegment(id=0, text="hello world clip", start=0.0, end=5.0, words=()),
        TranscriptSegment(id=1, text="another moment here", start=5.0, end=12.0, words=()),
    ]
    return Transcript(segments=segs, language="en", duration=duration, source_path=Path("x"))


def test_audio_analyser_onset_curve(tmp_path):
    fake_librosa = MagicMock()
    y = np.zeros(22050)
    fake_librosa.load.return_value = (y, 22050)
    fake_librosa.feature.rms.return_value = np.array([[0.1, 0.5]])
    fake_librosa.onset.onset_strength.return_value = np.array([0.2, 0.8])
    fake_librosa.times_like.side_effect = [
        np.array([0.0, 0.5]),
        np.array([0.0, 0.5]),
    ]
    video = tmp_path / "v.mp4"
    video.write_bytes(b"x")
    with patch.dict("sys.modules", {"librosa": fake_librosa}):
        analyser = _AudioAnalyser(video)
    times, onset = analyser.onset_curve()
    assert len(times) == len(onset)


def test_optical_flow_analyser_computes_scores(tmp_path):
    video = tmp_path / "flow.mp4"
    video.write_bytes(b"x")
    frame = np.zeros((180, 320, 3), dtype=np.uint8)
    gray = np.zeros((180, 320), dtype=np.uint8)
    flow = np.zeros((180, 320, 2), dtype=np.float32)
    flow[..., 0] = 0.5
    flow[..., 1] = 0.5

    cap = MagicMock()
    cap.get.return_value = 30.0
    cap.read.side_effect = [(True, frame), (True, frame), (False, None)]

    with patch("core.highlights.cv2.VideoCapture", return_value=cap), \
         patch("core.highlights.cv2.cvtColor", return_value=gray), \
         patch("core.highlights.cv2.resize", return_value=gray), \
         patch("core.highlights.cv2.calcOpticalFlowFarneback", return_value=flow):
        analyser = _OpticalFlowAnalyser(video, sample_fps=30.0)
        score = analyser.score(0.0, 2.0)
    assert 0.0 <= score <= 1.0


def test_snap_boundaries_short_source_duration():
    tr = _transcript(duration=10.0)
    s, e = _snap_boundaries(
        1.0, 4.0, tr,
        padding=0.5, min_dur=15.0, max_dur=90.0,
        source_duration=10.0,
    )
    assert s == 0.0
    assert e == 10.0


def test_guaranteed_clips_long_source_multiple_chunks():
    tr = _transcript(duration=600.0)
    hcfg = get_settings().highlight
    clips = _guaranteed_clips(tr, hcfg)
    assert len(clips) >= 1
    assert all(c.end > c.start for c in clips)


def test_nms_fallback_when_all_overlap():
    cfg = get_settings()
    base = ClipCandidate(
        segment_id=0, start=0.0, end=10.0, text="a",
        scores=SignalScores(), llm_hook="", llm_title="",
        emotion=Emotion.NEUTRAL, meme_keywords=[],
    )
    dup = ClipCandidate(
        segment_id=1, start=1.0, end=9.0, text="b",
        scores=SignalScores(), llm_hook="", llm_title="",
        emotion=Emotion.NEUTRAL, meme_keywords=[],
    )
    dup.scores.set_ensemble(0.1)
    base.scores.set_ensemble(0.9)
    kept = _nms([base, dup], iou_threshold=0.25)
    assert len(kept) == 1


def test_find_highlights_nms_fallback_to_guaranteed(tmp_path):
    from core.content_profiles import get_profile

    cfg = get_settings(reload=True)
    cfg.highlight.target_clips = 1
    cfg.highlight.candidate_mode = "segments"
    video = tmp_path / "short.mp4"
    video.write_bytes(b"x")
    tr = _transcript(duration=30.0)

    cand = ClipCandidate(
        segment_id=0, start=0.0, end=20.0, text="moment",
        scores=SignalScores(), llm_hook="", llm_title="",
        emotion=Emotion.NEUTRAL, meme_keywords=[],
    )
    cand.scores.set_ensemble(0.5)

    fake_audio = MagicMock()
    fake_audio.energy.return_value = 0.5
    fake_audio.novelty.return_value = 0.5
    fake_audio.energy_curve.return_value = (np.array([0.0]), np.array([0.5]))
    fake_audio.onset_curve.return_value = (np.array([0.0]), np.array([0.5]))

    with patch("core.highlights._AudioAnalyser", return_value=fake_audio), \
         patch("core.highlights._OpticalFlowAnalyser") as flow_cls, \
         patch("core.highlights.EnsembleScorer.score_segment", return_value=cand), \
         patch("core.highlights._discover_peak_windows", return_value=[]), \
         patch("core.highlights._nms", return_value=[]):
        flow_cls.return_value.score.return_value = 0.0
        out = find_highlights(tr, video, cfg, pipeline_hints={"skip_optical_flow": True})
    assert len(out) >= 1


def test_discover_peak_windows_empty_energy_curve(tmp_path):
    from core.content_profiles import get_profile

    cfg = get_settings()
    video = tmp_path / "v.mp4"
    video.write_bytes(b"x")
    # librosa is imported locally inside __init__ — patch via sys.modules
    import librosa as _librosa_real
    mock_lib = MagicMock(spec=_librosa_real)
    mock_lib.load.return_value = (np.zeros(22050), 22050)
    mock_lib.feature.rms.return_value = np.zeros((1, 10))
    mock_lib.times_like.return_value = np.linspace(0, 5, 10)
    mock_lib.onset.onset_strength.return_value = np.zeros(10)
    with patch.dict("sys.modules", {"librosa": mock_lib}):
        scorer = EnsembleScorer(video, cfg, skip_optical_flow=True)
    scorer._audio._y = np.array([])  # noqa: SLF001
    scorer._audio._sr = 22050  # noqa: SLF001
    scorer._audio.energy_curve = MagicMock(return_value=(np.array([]), np.array([])))  # noqa: SLF001
    windows = _discover_peak_windows(
        scorer, None, duration=120.0, hcfg=cfg.highlight, profile=get_profile("gaming"),
    )
    assert windows == []
