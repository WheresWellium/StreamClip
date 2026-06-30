"""Tests for creator content profile weights."""

from __future__ import annotations

from core.content_profiles import get_profile, list_profiles


def test_profiles_sum_weights_to_one() -> None:
    for entry in list_profiles():
        p = get_profile(entry["id"])
        total = (
            p.weight_audio_energy
            + p.weight_spectral_novelty
            + p.weight_optical_flow
            + p.weight_chat_spikes
            + p.weight_llm_virality
        )
        assert 0.999 < total < 1.001, entry["id"]


def test_unknown_profile_falls_back_to_general() -> None:
    p = get_profile("unknown")
    g = get_profile("general")
    assert p.weight_audio_energy == g.weight_audio_energy
