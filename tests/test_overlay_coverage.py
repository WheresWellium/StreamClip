"""Overlay module mocked coverage."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock, patch
from core.config import get_settings
from core.models import ClipCandidate, Emotion, SignalScores
from core import overlay as ov

def _cand():
    return ClipCandidate(
        segment_id=0, start=0.0, end=5.0, text="hook text", scores=SignalScores(),
        llm_hook="big clutch", llm_title="t", emotion=Emotion.HYPE, meme_keywords=["clutch"],
    )

def test_apply_overlays_no_assets(tmp_path):
    cfg = get_settings(reload=True)
    inp = tmp_path / "in.mp4"
    out = tmp_path / "out.mp4"
    inp.write_bytes(b"v")
    with patch.object(ov, "load_manifest", return_value=[]):
        path, applied = ov.apply_overlays(inp, out, _cand(), cfg)
    assert path == out
    assert applied == []

def test_write_stub_manifest(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    out = tmp_path / "manifest.json"
    ov._write_stub_manifest(assets, out)
    assert out.exists()

def test_probe_duration(tmp_path):
    p = tmp_path / "c.mp4"
    p.write_bytes(b"x")
    with patch.object(ov.subprocess, "run", return_value=MagicMock(stdout='{"format":{"duration":1.5}}', returncode=0)):
        assert ov._probe_duration(p) == 1.5
