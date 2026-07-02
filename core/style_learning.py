"""Channel style learning from clip feedback."""

from __future__ import annotations

from typing import Any

from core.content_profiles import ContentProfile, get_profile


def apply_feedback_to_user_weights(
    current: dict[str, Any] | None,
    *,
    profile: str,
    rating: int,
    clip_scores: dict[str, float],
) -> dict[str, Any]:
    """
    Nudge per-profile signal weights based on thumbs up/down.

    Positive feedback (rating >= 4) slightly boosts signals that were strong
    on the clip; negative feedback (rating <= 2) dampens them.
    """
    base = dict(current or {})
    key = profile if profile in (
        "gaming", "irl", "podcast", "esports", "general",
        "vlog", "education", "sports", "music",
    ) else "general"
    profile_key: ContentProfile = key  # type: ignore[assignment]

    stored = dict(base.get(key, {}))
    defaults = get_profile(profile_key)
    weights = {
        "weight_audio_energy": float(stored.get("weight_audio_energy", defaults.weight_audio_energy)),
        "weight_spectral_novelty": float(
            stored.get("weight_spectral_novelty", defaults.weight_spectral_novelty),
        ),
        "weight_optical_flow": float(stored.get("weight_optical_flow", defaults.weight_optical_flow)),
        "weight_chat_spikes": float(stored.get("weight_chat_spikes", defaults.weight_chat_spikes)),
        "weight_llm_virality": float(stored.get("weight_llm_virality", defaults.weight_llm_virality)),
    }

    delta = 0.02 if rating >= 4 else (-0.02 if rating <= 2 else 0.0)
    if delta == 0.0:
        return base

    signal_map = {
        "weight_audio_energy": clip_scores.get("audio", 0.0),
        "weight_spectral_novelty": clip_scores.get("spectral", 0.0),
        "weight_optical_flow": clip_scores.get("flow", 0.0),
        "weight_chat_spikes": clip_scores.get("chat", 0.0),
        "weight_llm_virality": clip_scores.get("llm", 0.0),
    }
    for wkey, strength in signal_map.items():
        if strength >= 0.5:
            weights[wkey] = max(0.0, min(1.0, weights[wkey] + delta))

    total = sum(weights.values()) or 1.0
    for wkey in weights:
        weights[wkey] /= total

    base[key] = weights
    return base


def merge_user_style_weights(
    profile: str,
    user_weights: dict[str, Any] | None,
) -> dict[str, float]:
    """Return highlight weights blending defaults with user-learned nudges."""
    defaults = get_profile(profile)
    if not user_weights or profile not in user_weights:
        return {
            "weight_audio_energy": defaults.weight_audio_energy,
            "weight_spectral_novelty": defaults.weight_spectral_novelty,
            "weight_optical_flow": defaults.weight_optical_flow,
            "weight_chat_spikes": defaults.weight_chat_spikes,
            "weight_llm_virality": defaults.weight_llm_virality,
        }
    learned = user_weights[profile]
    blend = 0.7
    return {
        "weight_audio_energy": blend * defaults.weight_audio_energy + (1 - blend) * float(
            learned.get("weight_audio_energy", defaults.weight_audio_energy),
        ),
        "weight_spectral_novelty": blend * defaults.weight_spectral_novelty + (1 - blend) * float(
            learned.get("weight_spectral_novelty", defaults.weight_spectral_novelty),
        ),
        "weight_optical_flow": blend * defaults.weight_optical_flow + (1 - blend) * float(
            learned.get("weight_optical_flow", defaults.weight_optical_flow),
        ),
        "weight_chat_spikes": blend * defaults.weight_chat_spikes + (1 - blend) * float(
            learned.get("weight_chat_spikes", defaults.weight_chat_spikes),
        ),
        "weight_llm_virality": blend * defaults.weight_llm_virality + (1 - blend) * float(
            learned.get("weight_llm_virality", defaults.weight_llm_virality),
        ),
    }
