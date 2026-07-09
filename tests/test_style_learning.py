"""Tests for channel style learning from clip feedback."""

from __future__ import annotations

from core.style_learning import apply_feedback_to_user_weights, merge_user_style_weights


def test_apply_feedback_positive_boosts_strong_signals():
    scores = {"audio": 0.9, "spectral": 0.1, "flow": 0.8, "chat": 0.0, "llm": 0.6}
    out = apply_feedback_to_user_weights(
        None,
        profile="gaming",
        rating=5,
        clip_scores=scores,
    )
    assert "gaming" in out
    weights = out["gaming"]
    assert abs(sum(weights.values()) - 1.0) < 1e-6
    assert weights["weight_audio_energy"] > 0


def test_apply_feedback_negative_dampens_strong_signals():
    # Only one strong signal so renormalization cannot mask the dampen.
    scores = {"audio": 0.9, "spectral": 0.0, "flow": 0.0, "chat": 0.0, "llm": 0.0}
    before = apply_feedback_to_user_weights(
        None,
        profile="irl",
        rating=5,
        clip_scores=scores,
    )
    after = apply_feedback_to_user_weights(
        before,
        profile="irl",
        rating=1,
        clip_scores=scores,
    )
    assert after["irl"]["weight_audio_energy"] < before["irl"]["weight_audio_energy"]


def test_apply_feedback_neutral_rating_is_noop():
    current = {"gaming": {"weight_audio_energy": 0.5}}
    out = apply_feedback_to_user_weights(
        current,
        profile="gaming",
        rating=3,
        clip_scores={"audio": 1.0},
    )
    assert out == current


def test_apply_feedback_unknown_profile_maps_to_general():
    out = apply_feedback_to_user_weights(
        None,
        profile="not-a-real-profile",
        rating=5,
        clip_scores={"audio": 0.9, "spectral": 0.0, "flow": 0.0, "chat": 0.0, "llm": 0.0},
    )
    assert "general" in out


def test_merge_user_style_weights_defaults_when_empty():
    merged = merge_user_style_weights("podcast", None)
    assert set(merged) == {
        "weight_audio_energy",
        "weight_spectral_novelty",
        "weight_optical_flow",
        "weight_chat_spikes",
        "weight_llm_virality",
    }


def test_merge_user_style_weights_blends_learned():
    learned = {
        "gaming": {
            "weight_audio_energy": 1.0,
            "weight_spectral_novelty": 0.0,
            "weight_optical_flow": 0.0,
            "weight_chat_spikes": 0.0,
            "weight_llm_virality": 0.0,
        },
    }
    defaults = merge_user_style_weights("gaming", None)
    blended = merge_user_style_weights("gaming", learned)
    assert blended["weight_audio_energy"] > defaults["weight_audio_energy"]


def test_apply_feedback_ignores_weak_signals():
    scores = {"audio": 0.1, "spectral": 0.2, "flow": 0.3, "chat": 0.4, "llm": 0.49}
    out = apply_feedback_to_user_weights(
        None,
        profile="vlog",
        rating=5,
        clip_scores=scores,
    )
    # No signal >= 0.5, so weights stay at profile defaults (still normalized).
    assert "vlog" in out
    assert abs(sum(out["vlog"].values()) - 1.0) < 1e-6


def test_merge_user_style_weights_missing_profile_key_uses_defaults():
    learned = {"gaming": {"weight_audio_energy": 1.0}}
    defaults = merge_user_style_weights("podcast", None)
    blended = merge_user_style_weights("podcast", learned)
    assert blended == defaults


def test_apply_feedback_clamps_weights_to_unit_interval():
    current = {
        "music": {
            "weight_audio_energy": 0.99,
            "weight_spectral_novelty": 0.01,
            "weight_optical_flow": 0.0,
            "weight_chat_spikes": 0.0,
            "weight_llm_virality": 0.0,
        },
    }
    out = apply_feedback_to_user_weights(
        current,
        profile="music",
        rating=5,
        clip_scores={"audio": 1.0, "spectral": 0.0, "flow": 0.0, "chat": 0.0, "llm": 0.0},
    )
    for value in out["music"].values():
        assert 0.0 <= value <= 1.0
