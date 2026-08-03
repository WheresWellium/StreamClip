"""Guards for render-matrix claims (fonts, preset divergence, fallback truth)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import core.captions as cap
import core.reframe as rf
from core.config import get_settings
from core.models import ClipCandidate, Emotion, SignalScores
from core.reframe import PRESETS


EXPECTED_CAPTION_FONTS = {
    "gaming_impact": "Impact",
    "tiktok_pop": "Arial Rounded MT Bold",
    "minimal_white": "Helvetica Neue",
    "podcast_clean": "SF Pro Display",
    "shorts_bold": "Impact",
    "karaoke_highlight": "Arial Black",
    "accessibility_clean": "Arial",
}


def test_caption_styles_declare_expected_fontnames():
    assert set(cap._STYLES) == set(EXPECTED_CAPTION_FONTS)
    for style_id, fontname in EXPECTED_CAPTION_FONTS.items():
        assert cap._STYLES[style_id].fontname == fontname, style_id


def test_resolve_caption_fontname_falls_back_when_missing(monkeypatch):
    monkeypatch.setattr(cap, "_installed_font_families", lambda: frozenset({"Arial", "Segoe UI"}))
    assert cap.resolve_caption_fontname("Helvetica Neue") == "Arial"
    assert cap.resolve_caption_fontname("SF Pro Display") == "Segoe UI"
    assert cap.resolve_caption_fontname("Impact") == "Arial"  # missing → chain ends Arial


def test_resolve_caption_fontname_keeps_installed(monkeypatch):
    monkeypatch.setattr(
        cap,
        "_installed_font_families",
        lambda: frozenset({"Helvetica Neue", "Impact", "Arial"}),
    )
    assert cap.resolve_caption_fontname("Helvetica Neue") == "Helvetica Neue"
    assert cap.resolve_caption_fontname("Impact") == "Impact"


def test_p0_reframe_presets_diverge_on_hud_and_pan():
    fps = PRESETS["fps_game"]
    irl = PRESETS["irl"]
    cinematic = PRESETS["cinematic_wide"]
    assert fps.hud_top > 0 and fps.hud_bottom > 0
    assert irl.hud_top == 0 and irl.hud_bottom == 0
    assert cinematic.hud_top == 0 and cinematic.hud_bottom == 0
    assert fps.max_pan_velocity > irl.max_pan_velocity
    assert cinematic.smooth_window > fps.smooth_window


def test_reframe_module_doc_does_not_claim_letterbox_fallback():
    doc = (rf.__doc__ or "").lower()
    assert "centre-crop" in doc or "center-crop" in doc
    assert "letterbox fallback" not in doc


def test_tracking_fallback_filter_is_center_crop_not_blur(tmp_path: Path):
    cfg = get_settings(reload=True)
    cfg.reframe.fallback_center_crop = True
    inp = tmp_path / "in.mp4"
    out = tmp_path / "out.mp4"
    inp.write_bytes(b"v")
    cand = ClipCandidate(
        segment_id=0,
        start=0.0,
        end=1.0,
        text="x",
        scores=SignalScores(),
        emotion=Emotion.NEUTRAL,
    )
    with patch.object(rf, "_reframe_with_tracking", side_effect=RuntimeError("boom")):
        with patch.object(rf.subprocess, "run") as run:
            rf.reframe(inp, out, cfg, cand)
            vf = " ".join(str(x) for x in run.call_args.args[0])
            assert "crop=" in vf
            assert "boxblur" not in vf
            assert "pad=" not in vf


def test_generate_captions_persists_ass_with_fontname(tmp_path: Path):
    cfg = get_settings(reload=True)
    cfg.caption.style = "shorts_bold"
    clip = tmp_path / "clip_00_vertical.mp4"
    out = tmp_path / "clip_00_captioned.mp4"
    clip.write_bytes(b"v")
    from core.models import Transcript, TranscriptSegment, Word

    w = Word(text="wow", start=0.0, end=0.4, probability=0.99)
    seg = TranscriptSegment(id=0, text="wow", start=0.0, end=1.0, words=(w,))
    tr = Transcript(segments=[seg], language="en", duration=1.0, source_path=clip)
    probe = MagicMock(
        stdout='{"streams":[{"codec_type":"video","width":1080,"height":1920}]}',
        returncode=0,
    )
    with patch.object(cap.subprocess, "run", side_effect=[probe, MagicMock(returncode=0)]):
        cap.generate_captions(clip, out, tr, 0.0, 1.0, cfg, emotion="hype")
    ass = out.with_suffix(".ass")
    assert ass.is_file()
    text = ass.read_text(encoding="utf-8")
    assert "Fontname=Impact" in text or ",Impact," in text
