"""Tests for creator option catalogs."""

from __future__ import annotations

from core.creator_options import (
    ASPECT_RATIO_IDS,
    CAPTION_STYLE_IDS,
    CONTENT_PROFILE_IDS,
    DEFAULT_ASPECT_RATIO,
    REFRAME_PRESET_IDS,
    aspect_ratio_dimensions,
    is_valid_aspect_ratio,
    is_valid_caption_style,
    is_valid_content_profile,
    is_valid_reframe_preset,
    list_aspect_ratios,
    list_caption_styles,
    list_content_profiles,
    list_reframe_presets,
)
from core.content_profiles import get_profile, list_profiles
from core.reframe import PRESETS


def test_catalog_counts() -> None:
    assert len(CONTENT_PROFILE_IDS) >= 9
    assert len(REFRAME_PRESET_IDS) >= 9
    assert len(CAPTION_STYLE_IDS) >= 8


def test_meta_lists_match_ids() -> None:
    assert [p["id"] for p in list_content_profiles()] == list(CONTENT_PROFILE_IDS)
    assert [p["id"] for p in list_reframe_presets()] == list(REFRAME_PRESET_IDS)
    assert [p["id"] for p in list_caption_styles()] == list(CAPTION_STYLE_IDS)


def test_reframe_presets_have_backend_params() -> None:
    for preset_id in REFRAME_PRESET_IDS:
        if preset_id == "auto":
            continue
        assert preset_id in PRESETS, preset_id


def test_validators() -> None:
    assert is_valid_content_profile("vlog")
    assert is_valid_reframe_preset("presentation")
    assert is_valid_caption_style("shorts_bold")
    assert not is_valid_caption_style("invalid_style")


def test_new_profiles_weights_sum() -> None:
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


def test_meta_includes_aspect_ratio() -> None:
    reframe = list_reframe_presets()[0]
    assert reframe["aspect_ratio"] == "9:16"
    assert "1080" in reframe["output_resolution"]


def test_aspect_ratio_catalog() -> None:
    assert DEFAULT_ASPECT_RATIO == "9:16"
    assert set(ASPECT_RATIO_IDS) >= {"9:16", "1:1", "4:5", "16:9", "2:3"}
    assert [o["id"] for o in list_aspect_ratios()] == list(ASPECT_RATIO_IDS)
    for option in list_aspect_ratios():
        w, h = option["width"], option["height"]
        rw, rh = (int(x) for x in option["id"].split(":"))
        # Pixel dimensions must exactly match the advertised ratio
        assert w * rh == h * rw, option["id"]
        assert min(w, h) >= 1080


def test_content_profile_recommendations_are_valid() -> None:
    """Every profile must recommend a real reframe preset and caption style,
    so choosing a content type actually configures the whole pipeline."""
    for profile in list_content_profiles():
        assert profile["recommended_reframe"] in REFRAME_PRESET_IDS, profile["id"]
        assert profile["recommended_captions"] in CAPTION_STYLE_IDS, profile["id"]


def test_aspect_ratio_validators_and_dimensions() -> None:
    assert is_valid_aspect_ratio("1:1")
    assert not is_valid_aspect_ratio("3:7")
    assert aspect_ratio_dimensions("16:9") == (1920, 1080)
    assert aspect_ratio_dimensions("4:5") == (1080, 1350)
    # Unknown ids fall back to the 9:16 default
    assert aspect_ratio_dimensions("nonsense") == (1080, 1920)
