"""Highlights ensemble, peaks, find_highlights coverage."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from core.config import get_settings
from core.content_profiles import get_profile
from core.highlights import (
    EnsembleScorer, _NullFlowAnalyser, _discover_peak_windows, _guaranteed_clips,
    _iou, _nms, _score_window, _snap_boundaries, find_highlights,
)
from core.chat_spikes import ChatEvent
from core.models import ClipCandidate, Emotion, SignalScores, Transcript, TranscriptSegment

def _transcript(duration=300.0, n=5):
    segs = []
    step = duration / n
    for i in range(n):
        segs.append(TranscriptSegment(id=i, start=i*step, end=(i+1)*step, text=f"seg{i} " * 12, words=()))
    return Transcript(segments=segs, language="en", duration=duration, source_path=Path("x.mp4"))

def test_iou_and_nms():
    assert _iou(0, 10, 5, 15) > 0
    assert _iou(0, 1, 10, 11) == 0.0
    s = SignalScores()
    s.set_ensemble(0.9)
    a = ClipCandidate(0,0,10,"a",s,"","",Emotion.NEUTRAL)
    b = ClipCandidate(1,0,10,"b",s,"","",Emotion.NEUTRAL)
    c = ClipCandidate(2,20,30,"c",s,"","",Emotion.NEUTRAL)
    kept = _nms([a,b,c], iou_threshold=0.3)
    assert len(kept) == 2

def test_snap_boundaries_short_source():
    t = _transcript(duration=30)
    s, e = _snap_boundaries(1, 5, t, padding=0.5, min_dur=3, max_dur=20, source_duration=30)
    assert e > s

@patch("core.highlights._AudioAnalyser")
@patch("core.highlights._OpticalFlowAnalyser")
def test_ensemble_scorer_with_chat(flow_cls, audio_cls, tmp_path):
    (tmp_path / "v.mp4").write_bytes(b"v")
    audio = audio_cls.return_value
    audio.energy.return_value = 0.7
    audio.novelty.return_value = 0.4
    flow_cls.return_value.score.return_value = 0.2
    chat = MagicMock()
    chat.score.return_value = 0.9
    cfg = get_settings(reload=True)
    scorer = EnsembleScorer(tmp_path / "v.mp4", cfg, chat_analyser=chat, skip_optical_flow=False)
    seg = TranscriptSegment(id=0, start=0, end=10, text="hello world enough words", words=())
    cand = scorer.score_segment(seg, 0)
    assert cand.rank_score > 0
    assert _NullFlowAnalyser().score(0, 1) == 0.0

@patch("core.highlights._AudioAnalyser")
def test_discover_peak_windows(audio_cls, tmp_path):
    (tmp_path / "v.mp4").write_bytes(b"v")
    audio = audio_cls.return_value
    audio.energy_curve.return_value = (
        np.linspace(0, 60, 61),
        np.array([0.1] * 30 + [0.95] + [0.1] * 30),
    )
    cfg = get_settings(reload=True)
    profile = get_profile("gaming")
    scorer = EnsembleScorer(tmp_path / "v.mp4", cfg, skip_optical_flow=True)
    chat = MagicMock()
    chat.per_second_curve.return_value = np.array([0.0] * 60 + [1.0])
    wins = _discover_peak_windows(
        scorer, chat, duration=61.0, hcfg=cfg.highlight, profile=profile,
    )
    assert isinstance(wins, list)

def test_guaranteed_clips():
    t = _transcript(duration=60, n=1)
    out = _guaranteed_clips(t, get_settings().highlight)
    assert len(out) >= 1

@patch("core.twitch_chat.fetch_vod_chat")
@patch("core.highlights._AudioAnalyser")
@patch("core.highlights._OpticalFlowAnalyser")
def test_find_highlights_hybrid(flow, audio, fetch, tmp_path, monkeypatch):
    vp = tmp_path / "v.mp4"
    vp.write_bytes(b"v")
    fetch.return_value = [ChatEvent(offset_secs=10.0, text="Pog")]
    audio.return_value.energy.return_value = 0.8
    audio.return_value.novelty.return_value = 0.5
    audio.return_value.energy_curve.return_value = (np.array([0.0, 30.0]), np.array([0.2, 0.9]))
    flow.return_value.score.return_value = 0.1
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.highlight, "candidate_mode", "hybrid")
    t = _transcript(duration=300, n=8)
    clips = find_highlights(
        t, vp, cfg,
        pipeline_hints={"skip_optical_flow": True, "has_chat_data": True, "content_profile": "gaming"},
        source_url="https://twitch.tv/v/1",
    )
    assert clips
