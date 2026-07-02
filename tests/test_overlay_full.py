"""Overlay apply path with mocked matcher/ffmpeg."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock, patch
from core.config import get_settings
from core.models import ClipCandidate, Emotion, SignalScores
from core.overlay import AssetRecord, apply_overlays

def _cand():
    return ClipCandidate(
        segment_id=0, start=0.0, end=5.0, text="x", scores=SignalScores(),
        llm_hook="insane clutch", llm_title="t", emotion=Emotion.HYPE, meme_keywords=["clutch"],
    )

def test_apply_overlays_with_assets(tmp_path):
    cfg = get_settings(reload=True)
    inp = tmp_path / "in.mp4"
    out = tmp_path / "out.mp4"
    asset = tmp_path / "a.gif"
    inp.write_bytes(b"v")
    asset.write_bytes(b"g")
    rec = AssetRecord(path=asset, asset_type="gif", description="hype", sfx_path=None,
                      default_duration=1.0, tags=["clutch"])
    matcher = MagicMock()
    matcher.query.return_value = [(rec, 0.99)]
    with patch("core.overlay.load_manifest", return_value=[rec]):
        with patch("core.overlay._get_matcher", return_value=matcher):
            with patch("core.overlay._probe_duration", return_value=5.0):
                with patch("core.overlay._find_audio_peak", return_value=1.0):
                    with patch("core.overlay.subprocess.run", return_value=MagicMock(returncode=0)):
                        path, applied = apply_overlays(inp, out, _cand(), cfg)
    assert applied
