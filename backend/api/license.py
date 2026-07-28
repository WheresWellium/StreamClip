"""License activation API for self-hosted Pro."""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import (
    LicenseActivationListRequest,
    LicenseActivationListResponse,
    LicenseActivationOut,
    LicenseActivationReleaseRequest,
    LicenseActivationReleaseResponse,
    LicenseActivateRequest,
    LicenseActivateResponse,
    LicenseStatusOut,
)
from backend.db.repositories import InstallLicenseRepository, UserRepository
from backend.db.session import get_db
from backend.middleware.auth import get_current_user_id
from backend.middleware.rate_limit import rate_limit_request
from backend.services.license_link import link_license_to_user
from core.commerce.lemon_squeezy_client import activate_license_with_ls
from core.commerce.entitlements import variant_tier
from core.config import get_settings
from core.errors import (
    ActivationLimitError,
    InvalidLicenseKeyError,
    LicenseRevokedError,
)
from core.licensing import (
    activate_license_key,
    clear_persisted_entitlement,
    get_install_tier,
    hash_license_key,
    load_persisted_entitlement,
    verify_entitlement_token,
)

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/license", tags=["license"])


async def _get_valid_license(repo: InstallLicenseRepository, license_key: str):
    key_hash = hash_license_key(license_key)
    lic = await repo.get_by_key_hash(key_hash)
    if lic is None:
        raise InvalidLicenseKeyError()
    if lic.status == "revoked":
        raise LicenseRevokedError()
    return lic, key_hash


async def _active_count(repo: InstallLicenseRepository, lic) -> int:
    method = getattr(type(repo), "count_active_activations", None)
    if method is not None:
        return int(await method(repo, lic))
    return int(lic.activation_count or 0)


async def _activation_for_machine(repo: InstallLicenseRepository, lic, machine_id: str):
    method = getattr(type(repo), "get_activation", None)
    if method is not None:
        return await method(repo, lic, machine_id)
    return None


async def _list_active_activations(repo: InstallLicenseRepository, lic):
    method = getattr(type(repo), "list_activations", None)
    if method is not None:
        return await method(repo, lic)
    if lic.machine_id and lic.status == "activated":
        return [
            type(
                "LegacyActivation",
                (),
                {
                    "machine_id": lic.machine_id,
                    "activated_at": lic.activated_at,
                    "last_seen_at": lic.activated_at,
                },
            )(),
        ]
    return []


@router.post(
    "/activate",
    response_model=LicenseActivateResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit_request)],
)
async def activate_license(
    body: LicenseActivateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[str | None, Depends(get_current_user_id)] = None,
) -> LicenseActivateResponse:
    """Activate a purchased key: verify it was issued by commerce, bind it
    to this machine, and return a signed entitlement JWT."""
    cfg = get_settings()
    repo = InstallLicenseRepository(db)

    # Audit trail: every attempt is logged with the key-hash prefix and
    # machine id — success or fail — for abuse investigation.
    key_hash = hash_license_key(body.license_key)
    audit = log.bind(hash_prefix=key_hash[:12], machine_id=body.machine_id)

    lic = await repo.get_by_key_hash(key_hash)
    if lic is None and cfg.commerce.lemon_squeezy_api_key:
        ls_result = await activate_license_with_ls(
            body.license_key,
            body.machine_id,
            api_key=cfg.commerce.lemon_squeezy_api_key,
        )
        if ls_result.ok:
            tier = variant_tier(ls_result.variant_id, cfg)
            order_id = str(ls_result.order_id) if ls_result.order_id else None
            lic = await repo.create_issued(
                license_key_hash=key_hash,
                tier=tier,
                order_id=order_id,
                customer_email=ls_result.customer_email,
            )
            audit.info(
                "license_ls_activate_seeded",
                variant_id=ls_result.variant_id,
                tier=tier.value,
            )
        else:
            audit.warning(
                "license_ls_activate_failed",
                error=ls_result.error,
            )

    if lic is None:
        audit.warning("license_activate_attempt", result="invalid_key")
        raise InvalidLicenseKeyError()
    if lic.status == "revoked":
        audit.warning("license_activate_attempt", result="revoked")
        raise LicenseRevokedError()

    existing_activation = await _activation_for_machine(repo, lic, body.machine_id)
    is_new_machine = existing_activation is None or existing_activation.status != "active"
    active_count = await _active_count(repo, lic)
    if is_new_machine and active_count >= cfg.licensing.max_activations:
        audit.warning(
            "license_activate_attempt",
            result="activation_limit",
            activation_count=active_count,
        )
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

    # Phase 3a — bind license to the master user identity: prefer the
    # authenticated user, fall back to a purchase-email match. Best-effort:
    # linkage must never fail an otherwise valid activation.
    try:
        if user_id is not None:
            await link_license_to_user(db, lic, user_id)
        elif getattr(lic, "user_id", None) is None and lic.customer_email:
            matched = await UserRepository(db).get_by_email(
                lic.customer_email.strip().lower(),
            )
            if matched is not None:
                await link_license_to_user(db, lic, matched.id)
    except Exception as exc:  # noqa: BLE001 — auxiliary linkage only
        log.warning("license_user_link_failed", license_id=lic.id, error=str(exc))

    await db.commit()
    audit.info(
        "license_activate_attempt",
        result="success",
        tier=entitlement.tier.value,
        new_machine=is_new_machine,
        linked_user=user_id or getattr(lic, "user_id", None),
    )
    return LicenseActivateResponse(
        tier=entitlement.tier.value,
        expires_at=entitlement.expires_at,
        entitlement_jwt=token,
    )


@router.post(
    "/activations",
    response_model=LicenseActivationListResponse,
    dependencies=[Depends(rate_limit_request)],
)
async def list_license_activations(
    body: LicenseActivationListRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LicenseActivationListResponse:
    """List active seats for a license key the user currently possesses."""
    cfg = get_settings()
    repo = InstallLicenseRepository(db)
    lic, key_hash = await _get_valid_license(repo, body.license_key)
    activations = await _list_active_activations(repo, lic)
    active_count = len(activations)
    log.info(
        "license_activations_listed",
        hash_prefix=key_hash[:12],
        active_count=active_count,
    )
    return LicenseActivationListResponse(
        activations=[
            LicenseActivationOut(
                machine_id=row.machine_id,
                activated_at=row.activated_at,
                last_seen_at=row.last_seen_at,
                is_current=row.machine_id == body.machine_id,
            )
            for row in activations
        ],
        max_activations=cfg.licensing.max_activations,
        active_count=active_count,
        tier=lic.tier.value,
    )


@router.post(
    "/activations/release",
    response_model=LicenseActivationReleaseResponse,
    dependencies=[Depends(rate_limit_request)],
)
async def release_license_activation(
    body: LicenseActivationReleaseRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LicenseActivationReleaseResponse:
    """Release a selected active seat for a license key."""
    cfg = get_settings()
    repo = InstallLicenseRepository(db)
    lic, key_hash = await _get_valid_license(repo, body.license_key)
    release_method = getattr(type(repo), "release_activation", None)
    released = (
        await release_method(repo, lic, body.target_machine_id)
        if release_method is not None
        else None
    )
    if released is None:
        raise HTTPException(status_code=404, detail="That active device was not found.")
    current_released = body.target_machine_id == body.machine_id
    if current_released:
        clear_persisted_entitlement(cfg)
    active_count = await _active_count(repo, lic)
    await db.commit()
    log.info(
        "license_activation_released",
        hash_prefix=key_hash[:12],
        target_machine_id=body.target_machine_id,
        current_released=current_released,
        active_count=active_count,
    )
    return LicenseActivationReleaseResponse(
        released_machine_id=body.target_machine_id,
        active_count=active_count,
        max_activations=cfg.licensing.max_activations,
        current_device_released=current_released,
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
