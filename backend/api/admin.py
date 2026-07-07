"""
StreamClip — Admin API

Operator-only endpoints. Requires an authenticated user with tier=admin.

POST /api/admin/licenses/{license_id}/revoke — revoke an issued license.
Revoked rows are retained so future activation attempts fail closed.
"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import InstallLicense, UserTier
from backend.db.repositories import InstallLicenseRepository, UserRepository
from backend.db.session import get_db
from backend.middleware.auth import require_user_id
from backend.middleware.rate_limit import rate_limit_request

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


async def require_admin(
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> str:
    """Reject any caller whose account tier is not admin."""
    user = await UserRepository(db).get(user_id)
    if user is None or user.tier != UserTier.ADMIN or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user_id


@router.post(
    "/licenses/{license_id}/revoke",
    dependencies=[Depends(rate_limit_request)],
)
async def revoke_license(
    license_id: str,
    admin_id: Annotated[str, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    repo = InstallLicenseRepository(db)
    lic = await repo.get(license_id)
    if lic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")

    already = lic.status == "revoked"
    if not already:
        await repo.revoke(lic)

        # Downgrade the linked user's tier to FREE if they have no other
        # activated license. Never deletes the user — only soft-adjusts tier.
        linked_user_id = lic.user_id
        if linked_user_id:
            other_active = await db.execute(
                select(InstallLicense.id).where(
                    InstallLicense.user_id == linked_user_id,
                    InstallLicense.status == "activated",
                    InstallLicense.id != lic.id,
                ).limit(1),
            )
            if other_active.scalar_one_or_none() is None:
                user = await UserRepository(db).get(linked_user_id)
                if user and user.tier != UserTier.FREE:
                    user.tier = UserTier.FREE
                    log.info(
                        "user_tier_downgraded_on_revoke",
                        user_id=linked_user_id,
                        license_id=license_id,
                    )

        await db.commit()
    log.info(
        "license_revoked",
        license_id=license_id,
        admin_id=admin_id,
        already_revoked=already,
        hash_prefix=lic.license_key_hash[:12],
    )
    return {
        "license_id": license_id,
        "status": "revoked",
        "note": (
            "Issued entitlement JWTs remain valid until their exp claim. "
            "A jti blocklist is required to invalidate them immediately — "
            "see BETA_KNOWN_ISSUES.md."
        ),
    }
