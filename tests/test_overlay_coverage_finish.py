"""Finish overlay module coverage gaps."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.config import ExportConfig, OverlayConfig, Settings
from core.models import ClipCandidate, Emotion, SignalScores
from core import overlay as ov


def _candidate() -> ClipCandidate:
    return ClipCandidate(
        segment_id=0,
        start=0.0,
        end=5.0,
        text="clutch play",
        scores=SignalScores(),
        llm_hook="insane clutch",
        llm_title="Clutch",
        emotion=Emotion.HYPE,
        meme_keywords=["clutch", "hype"],
    )


def test_load_manifest_writes_stub_when_missing(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    manifest = assets / "manifest.json"

    def fake_write(assets_dir, out):
        out.write_text("[]", encoding="utf-8")

    with patch.object(ov, "_write_stub_manifest", side_effect=fake_write) as stub:
        result = ov.load_manifest(assets)
        stub.assert_called_once()
    assert result == []


def test_apply_overlays_disabled_copies_input(tmp_path):
    inp = tmp_path / "in.mp4"
    out = tmp_path / "out.mp4"
    inp.write_bytes(b"video")
    cfg = Settings(overlay=OverlayConfig(enabled=False))
    path, applied = ov.apply_overlays(inp, out, _candidate(), cfg)
    assert path == out
    assert out.read_bytes() == b"video"
    assert applied == []


def test_apply_overlays_appear_at_peak(tmp_path):
    inp = tmp_path / "in.mp4"
    out = tmp_path / "out.mp4"
    inp.write_bytes(b"video")
    assets = tmp_path / "assets"
    assets.mkdir()
    gif = assets / "gifs"
    gif.mkdir(parents=True)
    (gif / "hype.gif").write_bytes(b"gif")
    manifest = assets / "manifest.json"
    manifest.write_text(
        json.dumps([{
            "path": "gifs/hype.gif",
            "type": "gif",
            "description": "hype clutch win",
            "duration": 1.5,
            "tags": ["hype"],
        }]),
        encoding="utf-8",
    )

    cfg = Settings(
        overlay=OverlayConfig(
            enabled=True,
            assets_dir=assets,
            semantic_threshold=0.0,
            max_overlays_per_clip=1,
            appear_at_peak=True,
        ),
    )

    record = ov.AssetRecord(
        path=gif / "hype.gif",
        asset_type="gif",
        description="hype clutch win",
        sfx_path=None,
        default_duration=1.5,
        tags=["hype"],
    )
    matcher = MagicMock()
    matcher.query.return_value = [(record, 0.99)]

    with patch.object(ov, "_get_matcher", return_value=matcher), \
         patch.object(ov, "_probe_duration", return_value=5.0), \
         patch.object(ov, "_find_audio_peak", return_value=2.0) as peak, \
         patch.object(ov.subprocess, "run", return_value=MagicMock(returncode=0)):
        path, applied = ov.apply_overlays(inp, out, _candidate(), cfg)
    peak.assert_called()
    assert path == out
    assert len(applied) == 1
