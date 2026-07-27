"""Single resolver for per-user tier limits.

Every quota check goes through here so a tier's advertised limits in
``core/billing.py`` are the only source of truth. Routers must never inline
numeric ceilings — that is how FREE users ended up with PRO asset quotas.
"""

from __future__ import annotations

import inspect

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import User, UserTier
from core.billing import TierLimits, get_tier_limits


async def resolve_user_tier(db: AsyncSession, user_id: str | None) -> UserTier:
    """Tier for a user id; anonymous or unknown callers get FREE."""
    if not user_id:
        return UserTier.FREE
    # AsyncSession.get is awaitable; some HTTP tests inject MagicMock sessions
    # whose ``.get`` returns a value synchronously.
    maybe = db.get(User, user_id)
    user = await maybe if inspect.isawaitable(maybe) else maybe
    return user.tier if user else UserTier.FREE


async def resolve_user_limits(db: AsyncSession, user_id: str | None) -> TierLimits:
    """Tier limits for a user id; anonymous or unknown callers get FREE limits."""
    return get_tier_limits(await resolve_user_tier(db, user_id))
