"""Tests for variant_tier mapping and capability resolution."""

from __future__ import annotations

from backend.db.models import UserTier
from core.commerce.entitlements import (
    CAPABILITY_AUDIO_INGEST,
    CAPABILITY_PUBLISHER,
    CAPABILITY_STUDIO,
    capabilities_for_tier,
    has_capability,
    resolve_capabilities,
    variant_tier,
)
from core.config import get_settings


def test_variant_tier_beta_maps_admin():
    cfg = get_settings()
    old_beta = cfg.commerce.lemon_squeezy_beta_variant_id
    old_pro = cfg.commerce.lemon_squeezy_pro_variant_id
    cfg.commerce.lemon_squeezy_beta_variant_id = "999"
    cfg.commerce.lemon_squeezy_pro_variant_id = "1000"
    try:
        assert variant_tier("999", cfg) is UserTier.ADMIN
        assert variant_tier("1000", cfg) is UserTier.PRO
        assert variant_tier("unknown", cfg) is UserTier.PRO
    finally:
        cfg.commerce.lemon_squeezy_beta_variant_id = old_beta
        cfg.commerce.lemon_squeezy_pro_variant_id = old_pro


def test_capabilities_for_legacy_pro_and_beta():
    assert capabilities_for_tier(UserTier.FREE) == []
    assert capabilities_for_tier(UserTier.PRO) == [
        CAPABILITY_STUDIO,
        CAPABILITY_PUBLISHER,
    ]
    assert CAPABILITY_AUDIO_INGEST in capabilities_for_tier(
        UserTier.PRO, audio_ingest=True
    )
    assert set(capabilities_for_tier(UserTier.ADMIN)) == {
        CAPABILITY_STUDIO,
        CAPABILITY_PUBLISHER,
        CAPABILITY_AUDIO_INGEST,
    }


def test_resolve_capabilities_prefers_stored():
    caps = resolve_capabilities(
        tier=UserTier.PRO,
        stored=[CAPABILITY_STUDIO],
        order_id="audio:123",
    )
    assert caps == [CAPABILITY_STUDIO]
    assert not has_capability(caps, CAPABILITY_PUBLISHER)


def test_resolve_capabilities_derives_audio_from_order():
    caps = resolve_capabilities(tier=UserTier.PRO, order_id="audio:abc")
    assert has_capability(caps, CAPABILITY_AUDIO_INGEST)
    assert has_capability(caps, CAPABILITY_PUBLISHER)
