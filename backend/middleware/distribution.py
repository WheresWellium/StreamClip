"""Distribution access gates."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import InstallLicense, User, UserTier
from backend.db.session import get_db
from backend.middleware.auth import require_user_id
from core.distribution.errors import DistributionProRequired


async def _install_has_pro_license(db: AsyncSession) -> bool:
    result = await db.execute(
        select(InstallLicense.id).where(InstallLicense.tier.in_([UserTier.PRO, UserTier.ADMIN])).limit(1),
    )
    return result.scalar_one_or_none() is not None


async def require_distribution_access(
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> str:
    """Pro SaaS tier, admin, or active self-hosted Pro install license."""
    user = await db.get(User, user_id)
    if user and user.tier in (UserTier.PRO, UserTier.ADMIN):
        return user_id
    if await _install_has_pro_license(db):
        return user_id
    raise DistributionProRequired()
