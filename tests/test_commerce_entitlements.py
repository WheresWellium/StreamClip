"""Tests for variant_tier mapping."""

from __future__ import annotations

from backend.db.models import UserTier
from core.commerce.entitlements import variant_tier
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
