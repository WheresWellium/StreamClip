"""Reframe smoothing window floor tests."""

from __future__ import annotations

from core.config import ReframeConfig
from core.reframe import (
    MIN_SMOOTH_WINDOW_FRAMES,
    PRESETS,
    _resolve_smooth_window,
    effective_hud_fractions,
)


def test_smooth_window_never_below_sixty():
    cfg = ReframeConfig(smooth_window_frames=60)
    # Preset value below floor is raised to MIN_SMOOTH_WINDOW_FRAMES
    preset = PRESETS["battle_royale"]
    assert preset.smooth_window == 60
    assert _resolve_smooth_window(preset, cfg) == MIN_SMOOTH_WINDOW_FRAMES


def test_smooth_window_uses_preset_when_higher():
    cfg = ReframeConfig(smooth_window_frames=60)
    preset = PRESETS["irl"]
    assert _resolve_smooth_window(preset, cfg) == 90


def test_effective_hud_fractions_gaming_uses_config_floor():
    cfg = ReframeConfig(hud_top_reserve=0.12, hud_bottom_reserve=0.20)
    top, bot = effective_hud_fractions(PRESETS["fps_game"], cfg)
    assert top >= 0.12
    assert bot >= 0.20


def test_effective_hud_fractions_irl_stays_zero():
    cfg = ReframeConfig(hud_top_reserve=0.12, hud_bottom_reserve=0.20)
    top, bot = effective_hud_fractions(PRESETS["irl"], cfg)
    assert top == 0.0
    assert bot == 0.0


def test_auto_preset_resolves_to_fps_game_hud_on_fallback(tmp_path):
    """auto → fps_game so FFmpeg fallback crop insets the kill-feed/HUD band."""
    from unittest.mock import MagicMock, patch

    from core.config import get_settings
    from core.models import ClipCandidate, Emotion, SignalScores
    from core import reframe as rf

    cfg = get_settings(reload=True)
    cfg.reframe.preset = "auto"
    cfg.reframe.fallback_center_crop = True
    inp = tmp_path / "in.mp4"
    out = tmp_path / "out.mp4"
    inp.write_bytes(b"v")
    cand = ClipCandidate(
        segment_id=0,
        start=0.0,
        end=3.0,
        text="x",
        scores=SignalScores(),
        llm_hook="h",
        llm_title="t",
        emotion=Emotion.CLUTCH,
    )

    captured: list[list[str]] = []

    def _run(cmd, **_kwargs):
        captured.append(list(cmd))
        return MagicMock(returncode=0)

    with patch.object(rf, "_reframe_with_tracking", side_effect=RuntimeError("fail")):
        with patch.object(rf.subprocess, "run", side_effect=_run):
            assert rf.reframe(inp, out, cfg, cand) == out

    assert captured, "expected ffmpeg fallback invoke"
    vf = " ".join(captured[0])
    # fps_game hud_top=0.10 → Y origin uses ih*0.1…
    assert "ih*0.1" in vf or "ih*0.10" in vf
    assert PRESETS["fps_game"].hud_top == 0.10
