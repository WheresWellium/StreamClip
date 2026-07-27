"""Distribution access gates."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import InstallLicense, User, UserTier
from backend.db.session import get_db
from backend.middleware.auth import require_user_id
from core.commerce.entitlements import (
    CAPABILITY_PUBLISHER,
    has_capability,
    resolve_capabilities,
    tier_implies_publisher,
)
from core.distribution.errors import DistributionProRequired


async def _install_has_publisher(db: AsyncSession) -> bool:
    result = await db.execute(
        select(InstallLicense).where(
            InstallLicense.status == "activated",
        ).limit(20),
    )
    for lic in result.scalars().all():
        caps = resolve_capabilities(
            tier=lic.tier,
            stored=getattr(lic, "capabilities", None),
            order_id=lic.order_id,
        )
        if has_capability(caps, CAPABILITY_PUBLISHER) or tier_implies_publisher(lic.tier):
            return True
    return False


async def require_distribution_access(
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> str:
    """Publisher capability, Pro/Admin user tier, or active install license."""
    user = await db.get(User, user_id)
    if user and tier_implies_publisher(user.tier):
        return user_id
    if await _install_has_publisher(db):
        return user_id
    raise DistributionProRequired()
