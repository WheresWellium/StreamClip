"""Tests for roadmap features."""

from __future__ import annotations

from core.billing import get_tier_limits
from core.style_learning import apply_feedback_to_user_weights, merge_user_style_weights
from core.subtitle_import import parse_srt
from backend.db.models import UserTier


def test_tier_limits_free():
    limits = get_tier_limits(UserTier.FREE)
    assert limits.max_target_clips == 5


def test_style_learning_feedback():
    weights = apply_feedback_to_user_weights(
        None,
        profile="gaming",
        rating=5,
        clip_scores={"audio": 0.9, "spectral": 0.2, "flow": 0.1, "chat": 0.0, "llm": 0.5},
    )
    assert "gaming" in weights
    merged = merge_user_style_weights("gaming", weights)
    assert abs(sum(merged.values()) - 1.0) < 0.01


def test_parse_srt_minimal(tmp_path):
    srt = tmp_path / "test.srt"
    srt.write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nHello world\n\n"
        "2\n00:00:02,500 --> 00:00:05,000\nSecond line\n",
        encoding="utf-8",
    )
    t = parse_srt(srt)
    assert t is not None
    assert len(t.segments) == 2
