"""
Phase 3a — Link install licenses to the master user identity.

Users are never deleted on license events; linkage is additive and
`users.is_active` is the only disable mechanism.
"""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import InstallLicense, User, UserTier
from backend.db.repositories import InstallLicenseRepository, UserRepository

log = structlog.get_logger(__name__)


def _sync_tier(user: User, lic_tier: UserTier) -> bool:
    """Upgrade a free user to the license tier (never downgrade)."""
    if user.tier == UserTier.FREE and lic_tier in (UserTier.PRO, UserTier.ADMIN):
        user.tier = lic_tier
        return True
    return False


async def link_license_to_user(
    db: AsyncSession,
    lic: InstallLicense,
    user_id: str,
) -> None:
    """Bind one license to a user (activation with auth) and sync tier."""
    await InstallLicenseRepository(db).link_user(lic, user_id)
    user = await UserRepository(db).get(user_id)
    if user is not None and _sync_tier(user, lic.tier):
        await db.flush()
    log.info("license_linked_to_user", license_id=lic.id, user_id=user_id)


async def link_licenses_by_email(db: AsyncSession, user: User) -> int:
    """
    Link all unlinked licenses purchased with this user's email
    (registration flow). Returns the number of licenses linked.
    """
    repo = InstallLicenseRepository(db)
    linked = await repo.link_by_email(user.email, user.id)
    if linked:
        # Any linked pro license upgrades a free account
        result = await db.execute(
            select(InstallLicense)
            .where(
                InstallLicense.user_id == user.id,
                InstallLicense.tier.in_((UserTier.PRO, UserTier.ADMIN)),
            )
            .limit(1),
        )
        lic = result.scalar_one_or_none()
        if lic is not None and _sync_tier(user, lic.tier):
            await db.flush()
        log.info("licenses_linked_by_email", user_id=user.id, count=linked)
    return linked
