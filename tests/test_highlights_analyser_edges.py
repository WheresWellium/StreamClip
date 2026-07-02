from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
from core.highlights import _AudioAnalyser, _OpticalFlowAnalyser, _guaranteed_clips, find_highlights
from core.models import Transcript, TranscriptSegment, Word

def test_audio_safe_norm_zero():
    assert _AudioAnalyser._safe_norm(np.zeros(3)).max() == 0

def test_audio_window_empty_mask(tmp_path):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"0")
    lib = MagicMock()
    lib.load.return_value = (np.array([0.0]), 22050)
    lib.feature.rms.return_value = np.array([[0.0]])
    lib.onset.onset_strength.return_value = np.array([0.0])
    lib.times_like.return_value = np.array([10.0])
    with patch.dict("sys.modules", {"librosa": lib}):
        a = _AudioAnalyser(video)
    assert a.energy(0.0, 1.0) == 0.0

def test_optical_flow_no_frames(tmp_path):
    video = tmp_path / "v.mp4"
    cap = MagicMock()
    cap.get.return_value = 30.0
    cap.read.return_value = (False, None)
    with patch("core.highlights.cv2.VideoCapture", return_value=cap):
        o = _OpticalFlowAnalyser(video)
        assert o.score(0.0, 1.0) == 0.0

def test_guaranteed_long_source():
    segs = [TranscriptSegment(id=i, start=i*60.0, end=(i+1)*60.0, text="word "*20, words=()) for i in range(10)]
    tr = Transcript(segments=segs, language="en", duration=600.0, source_path=Path("x.mp4"))
    from core.config import get_settings
    clips = _guaranteed_clips(tr, get_settings().highlight)
    assert len(clips) >= 1

def test_find_highlights_cap_pool(tmp_path, monkeypatch):
    from core.config import get_settings
    from core.models import ClipCandidate, Emotion, SignalScores
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.highlight, "target_clips", 2)
    video = tmp_path / "v.mp4"
    video.write_bytes(b"0")
    segs = []
    for i in range(40):
        segs.append(TranscriptSegment(id=i, start=float(i), end=float(i+1), text="hello world "*5, words=()))
    tr = Transcript(segments=segs, language="en", duration=300.0, source_path=video)
    mock_scorer = MagicMock()
    mock_scorer.score_segment.side_effect = lambda seg, idx: ClipCandidate(
        segment_id=idx, start=seg.start, end=seg.end, text=seg.text, scores=SignalScores(),
        llm_hook="", llm_title="", emotion=Emotion.NEUTRAL,
    )
    mock_scorer._audio = MagicMock()
    mock_scorer._audio.energy_curve.return_value = (np.array([0.0, 1.0]), np.array([0.1, 0.9]))
    monkeypatch.setattr("core.highlights.EnsembleScorer", lambda *a, **k: mock_scorer)
    monkeypatch.setattr(cfg.highlight, "candidate_mode", "segments")
    clips = find_highlights(tr, video, cfg, pipeline_hints={"skip_optical_flow": True})
    assert len(clips) <= cfg.highlight.target_clips
