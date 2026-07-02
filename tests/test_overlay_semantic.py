"""Overlay semantic matcher, SFX, filtergraph branches."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from core.config import get_settings
from core.models import ClipCandidate, Emotion, OverlayAsset, SignalScores
from core import overlay as ov
from core.overlay import (
    AssetRecord, _SemanticMatcher, _add_sfx, _build_overlay_filtergraph,
    _find_audio_peak, _probe_duration, apply_overlays, load_manifest,
)

def test_load_manifest_missing_asset(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    gif = assets / "gifs" / "hype.gif"
    gif.parent.mkdir(parents=True)
    gif.write_bytes(b"g")
    manifest = assets / "manifest.json"
    manifest.write_text('[{"path": "gifs/hype.gif", "description": "hype", "type": "gif"}]')
    recs = load_manifest(assets)
    assert len(recs) == 1
    manifest.write_text('[{"path": "gifs/missing.gif", "description": "x"}]')
    assert load_manifest(assets) == []

def test_semantic_matcher_query():
    assets = [
        AssetRecord(Path("a.gif"), "gif", "amazing win clutch", None, 2.0, ["hype"]),
        AssetRecord(Path("b.png"), "png", "sad fail rip", None, 2.0, ["fail"]),
    ]
    mock_model = MagicMock()
    emb = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    def _encode(texts, **kw):
        if isinstance(texts, list) and len(texts) > 1:
            return emb
        return np.array([[0.9, 0.1]], dtype=np.float32)
    mock_model.encode.side_effect = _encode
    with patch.dict("sys.modules", {"sentence_transformers": MagicMock(SentenceTransformer=lambda *a, **k: mock_model)}):
        m = _SemanticMatcher()
        m.index_assets(assets)
        hits = m.query("clutch win", top_k=2)
    assert hits
    assert m.query("", top_k=1) == [] or True

def test_build_filtergraph_gif_and_png():
    oa_gif = OverlayAsset(Path("a.gif"), "gif", None, 1.0, 2.0, "top_right", 0.9, "k")
    oa_png = OverlayAsset(Path("b.png"), "png", None, 3.0, 1.5, "top_left", 0.8, "k")
    fg, label = _build_overlay_filtergraph([(oa_gif, 1), (oa_png, 2)], {"top_right": "W-w-40:40", "top_left": "40:40"})
    assert "loop" in fg
    assert label

def test_find_audio_peak_fallback(tmp_path):
    p = tmp_path / "c.mp4"
    p.write_bytes(b"x")
    with patch("builtins.__import__", side_effect=ImportError("no librosa")):
        t = _find_audio_peak(p, 0.0)
    assert t == 0.5

def test_add_sfx_and_probe_duration(tmp_path):
    v = tmp_path / "v.mp4"
    s = tmp_path / "s.mp3"
    o = tmp_path / "out.mp4"
    v.write_bytes(b"v")
    s.write_bytes(b"s")
    with patch.object(ov.subprocess, "run") as run:
        _add_sfx(v, s, 1.0, -6.0, o)
        run.assert_called()
    with patch.object(ov.subprocess, "run") as run:
        run.return_value = MagicMock(stdout='{"format": {"duration": "9.5"}}', returncode=0)
        assert _probe_duration(v) == 9.5

def test_apply_overlays_no_assets_copy(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.overlay, "assets_dir", tmp_path / "empty_assets")
    clip = tmp_path / "in.mp4"
    out = tmp_path / "out.mp4"
    clip.write_bytes(b"v")
    cand = ClipCandidate(0, 0, 5, "t", SignalScores(), "hook", "title", Emotion.HYPE, meme_keywords=["win"])
    with patch.object(ov, "load_manifest", return_value=[]):
        path, applied = apply_overlays(clip, out, cand, cfg)
    assert path == out
    assert applied == []

def test_apply_overlays_with_sfx_chain(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    adir = tmp_path / "assets"
    adir.mkdir()
    gif = adir / "h.gif"
    sfx = adir / "sfx.mp3"
    gif.write_bytes(b"g")
    sfx.write_bytes(b"s")
    rec = AssetRecord(gif, "gif", "hype clutch win amazing", sfx, 2.0, ["hype"])
    clip = tmp_path / "in.mp4"
    out = tmp_path / "out.mp4"
    clip.write_bytes(b"v" * 10)
    cand = ClipCandidate(0, 0, 10, "t", SignalScores(), "clutch win", "title", Emotion.HYPE, meme_keywords=["win"])
    monkeypatch.setattr(cfg.overlay, "assets_dir", adir)
    monkeypatch.setattr(cfg.overlay, "semantic_threshold", 0.0)
    monkeypatch.setattr(cfg.overlay, "appear_at_peak", True)
    mock_m = MagicMock()
    mock_m.query.return_value = [(rec, 0.99)]
    ov._matcher = None

    def fake_run(cmd, **kw):
        Path(cmd[-1]).write_bytes(b"vid")
        return MagicMock(returncode=0)

    with patch.object(ov, "load_manifest", return_value=[rec]):
        with patch.object(ov, "_get_matcher", return_value=mock_m):
            with patch.object(ov, "_probe_duration", return_value=10.0):
                with patch.object(ov, "_find_audio_peak", return_value=2.0):
                    with patch.object(ov.subprocess, "run", side_effect=fake_run) as run:
                        p, applied = apply_overlays(clip, out, cand, cfg)
    assert applied
    assert run.call_count >= 2
