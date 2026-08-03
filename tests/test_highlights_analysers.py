"""Highlights analysers and boundaries with mocks."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from core.config import get_settings
from core.highlights import (
    EnsembleScorer,
    _AudioAnalyser,
    _NullAudioAnalyser,
    _OpticalFlowAnalyser,
    _snap_boundaries,
    find_highlights,
)
from core.models import Transcript, ClipCandidate, Emotion, SignalScores, TranscriptSegment, Word

def test_audio_analyser_window_means(tmp_path):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"0")
    lib = MagicMock()
    lib.load.return_value = (np.array([0.0, 1.0, 0.5]), 22050)
    lib.feature.rms.return_value = np.array([[0.2, 0.8]])
    lib.onset.onset_strength.return_value = np.array([0.1, 0.9])
    lib.times_like.side_effect = [np.array([0.0, 0.5]), np.array([0.0, 0.5])]
    with patch.dict("sys.modules", {"librosa": lib}):
        with patch(
            "core.highlights._load_mono_audio",
            return_value=(np.array([0.0, 1.0, 0.5]), 22050),
        ):
            a = _AudioAnalyser(video)
    assert a.energy(0.0, 1.0) >= 0
    assert a.novelty(0.0, 1.0) >= 0
    t, c = a.energy_curve()
    assert len(t) == len(c)

def test_ensemble_scorer_degrades_without_librosa(tmp_path):
    cfg = get_settings(reload=True)
    video = tmp_path / "v.mp4"
    video.write_bytes(b"0")
    with patch("core.highlights._AudioAnalyser", side_effect=ImportError("no librosa")):
        scorer = EnsembleScorer(video, cfg, skip_optical_flow=True)
    assert isinstance(scorer._audio, _NullAudioAnalyser)
    assert scorer._audio.energy(0.0, 1.0) == 0.0


def test_optical_flow_analyser(tmp_path):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"0")
    frame = np.zeros((180, 320, 3), dtype=np.uint8)
    cap = MagicMock()
    cap.get.return_value = 30.0
    cap.read.side_effect = [(True, frame), (True, frame), (False, None)]
    with patch("core.highlights.cv2.VideoCapture", return_value=cap):
        with patch("core.highlights.cv2.cvtColor", return_value=np.zeros((180, 320))):
            with patch("core.highlights.cv2.resize", side_effect=lambda g, s: g):
                with patch("core.highlights.cv2.calcOpticalFlowFarneback", return_value=np.ones((180, 320, 2))):
                    o = _OpticalFlowAnalyser(video)
                    assert o.score(0.0, 2.0) >= 0

def test_snap_boundaries():
    w = Word(text="a", start=0.0, end=0.5, probability=0.9)
    seg = TranscriptSegment(id=0, text="hello", start=0.0, end=10.0, words=(w,))
    tr = Transcript(segments=[seg], language="en", duration=30.0, source_path=Path("x"))
    s, e = _snap_boundaries(1.0, 8.0, tr, source_duration=30.0)
    assert s < e

def test_find_highlights_with_chat_mock(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    video = tmp_path / "v.mp4"
    video.write_bytes(b"0")
    w = Word(text="wow", start=0.0, end=0.5, probability=0.9)
    seg = TranscriptSegment(id=0, text="wow moment", start=0.0, end=12.0, words=(w,))
    tr = Transcript(segments=[seg], language="en", duration=60.0, source_path=video)
    mock_scorer = MagicMock()
    mock_scorer.score_segment.return_value = ClipCandidate(
        segment_id=0, start=0.0, end=12.0, text="wow", scores=SignalScores(),
        llm_hook="h", llm_title="t", emotion=Emotion.HYPE,
    )
    monkeypatch.setattr("core.highlights.EnsembleScorer", lambda *a, **k: mock_scorer)
    with patch("core.twitch_chat.fetch_vod_chat", return_value=[]):
        clips = find_highlights(tr, video, cfg, source_url="https://twitch.tv/videos/1")
    assert isinstance(clips, list)
