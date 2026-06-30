"""Reframe smoothing window floor tests."""

from __future__ import annotations

from core.config import ReframeConfig
from core.reframe import MIN_SMOOTH_WINDOW_FRAMES, PRESETS, _resolve_smooth_window


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
