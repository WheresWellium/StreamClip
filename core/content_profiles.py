"""
Creator content profiles — tuned highlight signal weights per vertical.

Lets gaming streamers, IRL creators, podcasters, and esports casters get
sensible defaults without manual weight tuning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ContentProfile = Literal["gaming", "irl", "podcast", "esports", "general"]


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
        weight_audio_energy=0.25,
        weight_spectral_novelty=0.15,
        weight_optical_flow=0.15,
        weight_chat_spikes=0.05,
        weight_llm_virality=0.40,
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
}


def get_profile(name: str | None) -> ProfileWeights:
    key = name if name in _PROFILES else "general"
    return _PROFILES[key]  # type: ignore[index]


def list_profiles() -> list[dict[str, str]]:
    return [
        {
            "id": "gaming",
            "label": "Gaming / Twitch",
            "description": "Fast action, chat spikes, motion-heavy gameplay.",
        },
        {
            "id": "irl",
            "label": "IRL / Just Chatting",
            "description": "Talking head, reactions, conversational peaks.",
        },
        {
            "id": "podcast",
            "label": "Podcast / Interview",
            "description": "Dialogue-driven; minimal motion weighting.",
        },
        {
            "id": "esports",
            "label": "Esports / Casted",
            "description": "Caster hype + on-screen action + chat.",
        },
        {
            "id": "general",
            "label": "General",
            "description": "Balanced defaults for mixed content.",
        },
    ]
