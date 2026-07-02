"""Reframe module mocked coverage."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch, MagicMock
from core.config import get_settings
from core.models import ClipCandidate, Emotion, SignalScores
from core import reframe as rf

def _cand():
    return ClipCandidate(
        segment_id=0, start=0.0, end=3.0, text="x", scores=SignalScores(),
        llm_hook="h", llm_title="t", emotion=Emotion.CLUTCH,
    )

def test_reframe_tracking_success(tmp_path):
    cfg = get_settings(reload=True)
    inp = tmp_path / "in.mp4"
    out = tmp_path / "out.mp4"
    inp.write_bytes(b"v")
    with patch.object(rf, "_reframe_with_tracking", return_value=out):
        assert rf.reframe(inp, out, cfg, _cand()) == out

def test_reframe_fallback_crop(tmp_path):
    cfg = get_settings(reload=True)
    cfg.reframe.preset = "auto"
    cfg.reframe.fallback_center_crop = True
    inp = tmp_path / "in.mp4"
    out = tmp_path / "out.mp4"
    inp.write_bytes(b"v")
    with patch.object(rf, "_reframe_with_tracking", side_effect=RuntimeError("fail")):
        with patch.object(rf.subprocess, "run", return_value=MagicMock(returncode=0)):
            assert rf.reframe(inp, out, cfg, _cand()) == out
