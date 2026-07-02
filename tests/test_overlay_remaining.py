from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from core.config import get_settings
from core.models import ClipCandidate, Emotion, SignalScores
from core import overlay as ov
from core.overlay import AssetRecord, _write_stub_manifest, apply_overlays, load_manifest

def test_write_stub_manifest(tmp_path):
    out = tmp_path / "manifest.json"
    _write_stub_manifest(tmp_path, out)
    assert out.exists()

def test_apply_overlays_below_threshold(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    adir = tmp_path / "assets"
    adir.mkdir()
    gif = adir / "h.gif"
    gif.write_bytes(b"g")
    (adir / "manifest.json").write_text('[{"path": "h.gif", "description": "hype", "type": "gif"}]')
    clip = tmp_path / "in.mp4"
    out = tmp_path / "out.mp4"
    clip.write_bytes(b"v")
    cand = ClipCandidate(0, 0, 5, "t", SignalScores(), "hook", "title", Emotion.HYPE)
    monkeypatch.setattr(cfg.overlay, "assets_dir", adir)
    monkeypatch.setattr(cfg.overlay, "semantic_threshold", 0.99)
    mock_m = MagicMock()
    rec = load_manifest(adir)[0]
    mock_m.query.return_value = [(rec, 0.1)]
    ov._matcher = None
    with patch.object(ov, "_get_matcher", return_value=mock_m):
        p, applied = apply_overlays(clip, out, cand, cfg)
    assert applied == []
