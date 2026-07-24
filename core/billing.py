"""Per-tier usage limits (billing is handled by Lemon Squeezy — see
backend/api/commerce.py and backend/api/license.py)."""

from __future__ import annotations

from dataclasses import dataclass

from backend.db.models import UserTier


@dataclass(frozen=True)
class TierLimits:
    max_target_clips: int
    max_jobs_per_month: int
    max_minutes_per_month: float
    max_templates: int
    max_assets: int
    max_vault_clips: int
    max_vault_bytes: int


_GB = 1024**3

TIER_LIMITS: dict[UserTier, TierLimits] = {
    UserTier.FREE: TierLimits(
        max_target_clips=5,
        max_jobs_per_month=30,
        max_minutes_per_month=600.0,
        max_templates=5,
        max_assets=10,
        max_vault_clips=25,
        max_vault_bytes=10 * _GB,
    ),
    UserTier.PRO: TierLimits(
        max_target_clips=20,
        max_jobs_per_month=500,
        max_minutes_per_month=10000.0,
        max_templates=20,
        max_assets=50,
        max_vault_clips=500,
        max_vault_bytes=50 * _GB,
    ),
    UserTier.ADMIN: TierLimits(
        max_target_clips=20,
        max_jobs_per_month=1_000_000,
        max_minutes_per_month=1_000_000.0,
        max_templates=100,
        max_assets=500,
        max_vault_clips=5000,
        max_vault_bytes=500 * _GB,
    ),
}


def get_tier_limits(tier: UserTier) -> TierLimits:
    return TIER_LIMITS.get(tier, TIER_LIMITS[UserTier.FREE])
