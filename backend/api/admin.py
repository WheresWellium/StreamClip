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
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import UserTier
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
        await db.commit()
    log.info(
        "license_revoked",
        license_id=license_id,
        admin_id=admin_id,
        already_revoked=already,
        hash_prefix=lic.license_key_hash[:12],
    )
    return {"license_id": license_id, "status": "revoked"}
