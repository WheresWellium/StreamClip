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
from core.errors import (
    ActivationLimitError,
    InvalidLicenseKeyError,
    LicenseRevokedError,
)
from core.licensing import (
    activate_license_key,
    get_install_tier,
    hash_license_key,
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
    """Activate a purchased key: verify it was issued by commerce, bind it
    to this machine, and return a signed entitlement JWT."""
    cfg = get_settings()
    repo = InstallLicenseRepository(db)

    lic = await repo.get_by_key_hash(hash_license_key(body.license_key))
    if lic is None:
        raise InvalidLicenseKeyError()
    if lic.status == "revoked":
        raise LicenseRevokedError()

    is_new_machine = lic.machine_id != body.machine_id
    if is_new_machine and (lic.activation_count or 0) >= cfg.licensing.max_activations:
        raise ActivationLimitError()

    token, entitlement = activate_license_key(
        body.license_key,
        body.machine_id,
        tier=lic.tier,
        cfg=cfg,
    )
    await repo.mark_activated(
        lic,
        machine_id=body.machine_id,
        entitlement_jwt=token,
        expires_at=entitlement.expires_at,
        count_activation=is_new_machine,
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
