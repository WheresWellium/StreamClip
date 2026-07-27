"""Tier limits come from core.billing, and monthly counters roll over."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.db.models import UserTier
from backend.db.repositories import QUOTA_PERIOD_DAYS, roll_quota_period
from backend.services.quota import resolve_user_limits, resolve_user_tier
from core.billing import get_tier_limits


def _user(**kw) -> SimpleNamespace:
    base = {
        "id": "u1",
        "tier": UserTier.FREE,
        "jobs_used_this_month": 0,
        "minutes_processed_this_month": 0.0,
        "quota_period_start": None,
    }
    base.update(kw)
    return SimpleNamespace(**base)


# ─── Lazy quota period rollover ──────────────────────────────────────────────

def test_first_use_anchors_the_period_without_resetting():
    user = _user(jobs_used_this_month=3)
    assert roll_quota_period(user) is False
    assert user.quota_period_start is not None
    assert user.jobs_used_this_month == 3


def test_counters_survive_inside_the_period():
    now = datetime.now(timezone.utc)
    user = _user(
        jobs_used_this_month=7,
        minutes_processed_this_month=45.0,
        quota_period_start=now - timedelta(days=QUOTA_PERIOD_DAYS - 1),
    )
    assert roll_quota_period(user, now=now) is False
    assert user.jobs_used_this_month == 7
    assert user.minutes_processed_this_month == 45.0


def test_counters_reset_once_the_period_lapses():
    now = datetime.now(timezone.utc)
    started = now - timedelta(days=QUOTA_PERIOD_DAYS + 2)
    user = _user(
        jobs_used_this_month=500,
        minutes_processed_this_month=9000.0,
        quota_period_start=started,
    )
    assert roll_quota_period(user, now=now) is True
    assert user.jobs_used_this_month == 0
    assert user.minutes_processed_this_month == 0.0
    assert user.quota_period_start == now


def test_naive_period_start_is_treated_as_utc():
    now = datetime.now(timezone.utc)
    user = _user(
        jobs_used_this_month=12,
        quota_period_start=(now - timedelta(days=QUOTA_PERIOD_DAYS + 1)).replace(tzinfo=None),
    )
    assert roll_quota_period(user, now=now) is True
    assert user.jobs_used_this_month == 0


# ─── Shared tier resolver ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_anonymous_callers_resolve_to_free_limits():
    db = SimpleNamespace(get=AsyncMock())
    assert await resolve_user_tier(db, None) is UserTier.FREE
    limits = await resolve_user_limits(db, None)
    assert limits.max_assets == get_tier_limits(UserTier.FREE).max_assets
    db.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_unknown_user_resolves_to_free_limits():
    db = SimpleNamespace(get=AsyncMock(return_value=None))
    limits = await resolve_user_limits(db, "ghost")
    assert limits.max_templates == get_tier_limits(UserTier.FREE).max_templates


@pytest.mark.asyncio
async def test_pro_user_resolves_to_pro_limits():
    db = SimpleNamespace(get=AsyncMock(return_value=_user(tier=UserTier.PRO)))
    limits = await resolve_user_limits(db, "u1")
    assert limits.max_assets == get_tier_limits(UserTier.PRO).max_assets
    assert limits.max_assets > get_tier_limits(UserTier.FREE).max_assets


# ─── Advertised limits stay distinct per tier ────────────────────────────────

def test_free_tier_limits_are_lower_than_pro():
    free = get_tier_limits(UserTier.FREE)
    pro = get_tier_limits(UserTier.PRO)
    assert free.max_assets < pro.max_assets
    assert free.max_templates < pro.max_templates
