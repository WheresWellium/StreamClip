"""License activation API for self-hosted Pro."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import (
    LicenseActivateRequest,
    LicenseActivateResponse,
    LicenseStatusOut,
)
from backend.db.repositories import InstallLicenseRepository
from backend.db.session import get_db
from backend.middleware.rate_limit import rate_limit_request
from core.config import get_settings
from core.licensing import (
    activate_license_key,
    get_install_tier,
    load_persisted_entitlement,
    verify_entitlement_token,
)

router = APIRouter(prefix="/api/license", tags=["license"])


@router.post(
    "/activate",
    response_model=LicenseActivateResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit_request)],
)
async def activate_license(
    body: LicenseActivateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LicenseActivateResponse:
    cfg = get_settings()
    token, entitlement = activate_license_key(
        body.license_key,
        body.machine_id,
        cfg=cfg,
    )
    repo = InstallLicenseRepository(db)
    await repo.upsert(
        license_key_hash=entitlement.license_key_hash,
        machine_id=body.machine_id,
        tier=entitlement.tier,
        entitlement_jwt=token,
        expires_at=entitlement.expires_at,
    )
    await db.commit()
    return LicenseActivateResponse(
        tier=entitlement.tier.value,
        expires_at=entitlement.expires_at,
        entitlement_jwt=token,
    )


@router.get(
    "/status",
    response_model=LicenseStatusOut,
    dependencies=[Depends(rate_limit_request)],
)
async def license_status(
    machine_id: str,
) -> LicenseStatusOut:
    cfg = get_settings()
    token = load_persisted_entitlement(cfg)
    if not token:
        return LicenseStatusOut(active=False, tier=get_install_tier(machine_id, cfg).value)
    try:
        ent = verify_entitlement_token(token, machine_id=machine_id, cfg=cfg)
        return LicenseStatusOut(
            active=True,
            tier=ent.tier.value,
            expires_at=ent.expires_at,
            machine_id=ent.machine_id,
        )
    except ValueError:
        return LicenseStatusOut(active=False, tier="free")
