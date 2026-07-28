"""License activation API for self-hosted Pro."""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import (
    LicenseActivateRequest,
    LicenseActivateResponse,
    LicenseStatusOut,
)
from backend.db.models import InstallLicense
from backend.db.repositories import InstallLicenseRepository, UserRepository
from backend.db.session import get_db
from backend.middleware.auth import get_current_user_id
from backend.middleware.rate_limit import rate_limit_request
from backend.services.license_link import link_license_to_user
from core.commerce.lemon_squeezy_client import activate_license_with_ls
from core.commerce.entitlements import (
    resolve_capabilities,
    tag_audio_order_id,
    variant_grants_audio_ingest,
    variant_tier,
)
from core.config import get_settings
from core.errors import (
    ActivationLimitError,
    InvalidLicenseKeyError,
    LicenseRevokedError,
)
from core.licensing import (
    activate_license_key,
    clear_persisted_entitlement,
    create_entitlement_token,
    get_install_tier,
    hash_license_key,
    license_is_perpetual,
    load_persisted_entitlement,
    persist_entitlement_token,
    verify_entitlement_token,
)

log = structlog.get_logger(__name__)

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
            caps = resolve_capabilities(
                tier=tier,
                order_id=order_id,
                variant_id=ls_result.variant_id,
                cfg=cfg,
            )
            if variant_grants_audio_ingest(ls_result.variant_id, cfg) and order_id:
                order_id = tag_audio_order_id(order_id)
            lic = await repo.create_issued(
                license_key_hash=key_hash,
                tier=tier,
                order_id=order_id,
                customer_email=ls_result.customer_email,
                capabilities=caps,
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

    is_new_machine = lic.machine_id != body.machine_id
    if is_new_machine and (lic.activation_count or 0) >= cfg.licensing.max_activations:
        audit.warning(
            "license_activate_attempt",
            result="activation_limit",
            activation_count=lic.activation_count,
        )
        raise ActivationLimitError()

    caps = resolve_capabilities(
        tier=lic.tier,
        stored=getattr(lic, "capabilities", None),
        order_id=getattr(lic, "order_id", None),
        cfg=cfg,
    )
    if not getattr(lic, "capabilities", None):
        lic.capabilities = caps

    token, entitlement = activate_license_key(
        body.license_key,
        body.machine_id,
        tier=lic.tier,
        capabilities=caps,
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
        capabilities=list(entitlement.capabilities),
    )


@router.get(
    "/status",
    response_model=LicenseStatusOut,
    dependencies=[Depends(rate_limit_request)],
)
async def license_status(
    machine_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LicenseStatusOut:
    """Report the local entitlement, re-verifying it against issued records.

    Tokens are deliberately short-lived: this endpoint renews a still-valid
    licence and tears down a revoked one, so revocation takes effect within a
    renewal window instead of lasting for the life of the JWT.
    """
    cfg = get_settings()
    token = load_persisted_entitlement(cfg)
    if not token:
        return LicenseStatusOut(
            active=False,
            tier=get_install_tier(machine_id, cfg).value,
            capabilities=[],
        )

    try:
        ent = verify_entitlement_token(token, machine_id=machine_id, cfg=cfg)
    except ValueError:
        # Expired or malformed: fall back to the issued records if we can.
        renewed = await _renew_from_records(db, machine_id, cfg)
        if renewed is not None:
            return renewed
        return LicenseStatusOut(active=False, tier="free", capabilities=[])

    lic = await InstallLicenseRepository(db).get_by_key_hash(ent.license_key_hash)
    if lic is not None and lic.status == "revoked":
        clear_persisted_entitlement(cfg)
        log.info("license_status_revoked", hash_prefix=ent.license_key_hash[:12])
        return LicenseStatusOut(active=False, tier="free", revoked=True, capabilities=[])

    caps = list(ent.capabilities)
    if lic is not None:
        caps = resolve_capabilities(
            tier=lic.tier,
            stored=getattr(lic, "capabilities", None) or caps,
            order_id=lic.order_id,
            cfg=cfg,
        )

    return LicenseStatusOut(
        active=True,
        tier=ent.tier.value,
        expires_at=ent.expires_at,
        machine_id=ent.machine_id,
        perpetual=license_is_perpetual(ent),
        capabilities=caps,
    )


async def _renew_from_records(
    db: AsyncSession,
    machine_id: str,
    cfg,
) -> LicenseStatusOut | None:
    """Re-issue a token for a machine whose licence is still activated."""
    result = await db.execute(
        select(InstallLicense).where(
            InstallLicense.machine_id == machine_id,
            InstallLicense.status == "activated",
        ).limit(1),
    )
    lic = result.scalar_one_or_none()
    if lic is None:
        clear_persisted_entitlement(cfg)
        return None

    caps = resolve_capabilities(
        tier=lic.tier,
        stored=getattr(lic, "capabilities", None),
        order_id=lic.order_id,
        cfg=cfg,
    )
    if not lic.capabilities:
        lic.capabilities = caps

    token = create_entitlement_token(
        tier=lic.tier,
        machine_id=machine_id,
        license_key_hash=lic.license_key_hash,
        expires_at=None if cfg.licensing.entitlement_days == 0 else lic.expires_at,
        capabilities=caps,
        cfg=cfg,
    )
    ent = verify_entitlement_token(token, machine_id=machine_id, cfg=cfg)
    persist_entitlement_token(token, cfg)
    log.info("license_token_renewed", hash_prefix=lic.license_key_hash[:12])
    return LicenseStatusOut(
        active=True,
        tier=ent.tier.value,
        expires_at=ent.expires_at,
        machine_id=machine_id,
        perpetual=license_is_perpetual(ent),
        capabilities=caps,
    )
