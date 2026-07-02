"""
Creator content profiles — tuned highlight signal weights per vertical.

Lets gaming streamers, IRL creators, podcasters, and esports casters get
sensible defaults without manual weight tuning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ContentProfile = Literal[
    "gaming", "irl", "podcast", "esports", "general",
    "vlog", "education", "sports", "music",
]


@dataclass(frozen=True)
class ProfileWeights:
    weight_audio_energy: float
    weight_spectral_novelty: float
    weight_optical_flow: float
    weight_chat_spikes: float
    weight_llm_virality: float
    peak_min_height: float
    peak_merge_gap_secs: float


_PROFILES: dict[ContentProfile, ProfileWeights] = {
    "gaming": ProfileWeights(
        # Chat weight matches the "chat spikes" promise in the profile copy;
        # it renormalizes away automatically when a source has no chat replay.
        weight_audio_energy=0.25,
        weight_spectral_novelty=0.15,
        weight_optical_flow=0.15,
        weight_chat_spikes=0.10,
        weight_llm_virality=0.35,
        peak_min_height=0.55,
        peak_merge_gap_secs=90.0,
    ),
    "irl": ProfileWeights(
        weight_audio_energy=0.35,
        weight_spectral_novelty=0.20,
        weight_optical_flow=0.05,
        weight_chat_spikes=0.10,
        weight_llm_virality=0.30,
        peak_min_height=0.50,
        peak_merge_gap_secs=120.0,
    ),
    "podcast": ProfileWeights(
        weight_audio_energy=0.40,
        weight_spectral_novelty=0.25,
        weight_optical_flow=0.0,
        weight_chat_spikes=0.0,
        weight_llm_virality=0.35,
        peak_min_height=0.48,
        peak_merge_gap_secs=150.0,
    ),
    "esports": ProfileWeights(
        weight_audio_energy=0.30,
        weight_spectral_novelty=0.15,
        weight_optical_flow=0.20,
        weight_chat_spikes=0.10,
        weight_llm_virality=0.25,
        peak_min_height=0.58,
        peak_merge_gap_secs=75.0,
    ),
    "general": ProfileWeights(
        weight_audio_energy=0.28,
        weight_spectral_novelty=0.18,
        weight_optical_flow=0.12,
        weight_chat_spikes=0.07,
        weight_llm_virality=0.35,
        peak_min_height=0.52,
        peak_merge_gap_secs=100.0,
    ),
    "vlog": ProfileWeights(
        weight_audio_energy=0.32,
        weight_spectral_novelty=0.18,
        weight_optical_flow=0.12,
        weight_chat_spikes=0.03,
        weight_llm_virality=0.35,
        peak_min_height=0.50,
        peak_merge_gap_secs=110.0,
    ),
    "education": ProfileWeights(
        weight_audio_energy=0.38,
        weight_spectral_novelty=0.22,
        weight_optical_flow=0.05,
        weight_chat_spikes=0.0,
        weight_llm_virality=0.35,
        peak_min_height=0.47,
        peak_merge_gap_secs=140.0,
    ),
    "sports": ProfileWeights(
        weight_audio_energy=0.32,
        weight_spectral_novelty=0.12,
        weight_optical_flow=0.28,
        weight_chat_spikes=0.03,
        weight_llm_virality=0.25,
        peak_min_height=0.56,
        peak_merge_gap_secs=70.0,
    ),
    "music": ProfileWeights(
        weight_audio_energy=0.45,
        weight_spectral_novelty=0.30,
        weight_optical_flow=0.10,
        weight_chat_spikes=0.0,
        weight_llm_virality=0.15,
        peak_min_height=0.54,
        peak_merge_gap_secs=80.0,
    ),
}


def get_profile(name: str | None) -> ProfileWeights:
    key = name if name in _PROFILES else "general"
    return _PROFILES[key]  # type: ignore[index]


def list_profiles() -> list[dict[str, str]]:
    from core.creator_options import list_content_profiles

    return list_content_profiles()
