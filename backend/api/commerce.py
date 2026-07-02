"""Lemon Squeezy webhook handler for license delivery.

Chain: purchase → LS webhook → issued license row → customer activates the
key (backend/api/license.py) → entitlement JWT → tier enforcement.

Two supported events:
  • ``license_key_created`` — LS generated the key and emails it to the
    customer natively. We persist its hash so activation can verify it.
  • ``order_created`` — fallback for stores without LS license keys enabled:
    we generate a key locally and return it in the webhook response (visible
    in the LS webhook log for manual delivery).
"""

from __future__ import annotations

import json
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import UserTier
from backend.db.repositories import InstallLicenseRepository
from backend.db.session import get_db
from core.commerce.lemon_squeezy import (
    generate_license_key,
    parse_order_event,
    verify_webhook_signature,
)
from core.config import get_settings
from core.licensing import hash_license_key

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/commerce", tags=["commerce"])


def _mask(key: str) -> str:
    return key[:10] + "…" if len(key) > 10 else "…"


@router.post("/webhooks/lemon-squeezy", status_code=status.HTTP_200_OK)
async def lemon_squeezy_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_signature: Annotated[str | None, Header(alias="X-Signature")] = None,
) -> dict:
    cfg = get_settings()
    secret = cfg.commerce.lemon_squeezy_webhook_secret
    if not secret:
        # Fail closed: without a shared secret every payload is forgeable.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Commerce webhook not configured (LEMON_SQUEEZY_WEBHOOK_SECRET unset)",
        )

    body = await request.body()
    if not verify_webhook_signature(body, x_signature or "", secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON") from exc

    event = parse_order_event(payload)
    log.info(
        "lemon_squeezy_webhook",
        event_name=event["event_name"],
        order_id=event["order_id"],
        email=event.get("customer_email"),
    )

    repo = InstallLicenseRepository(db)

    if event["event_name"] == "license_key_created" and event["license_key_hash"]:
        # LS generated + delivers the key; we only need the hash to verify activation.
        if await repo.get_by_key_hash(event["license_key_hash"]) is None:
            await repo.create_issued(
                license_key_hash=event["license_key_hash"],
                tier=UserTier.PRO,
                order_id=event["order_id"] or None,
                customer_email=event.get("customer_email"),
            )
            await db.commit()
            log.info("license_recorded", order_id=event["order_id"])
        return {"status": "ok"}

    if event["event_name"] == "order_created":
        if event["order_id"]:
            existing = await repo.get_by_order_id(event["order_id"])
            if existing is not None:
                log.info("license_already_issued", order_id=event["order_id"])
                return {"status": "ok", "license_key": None}
        license_key = generate_license_key()
        await repo.create_issued(
            license_key_hash=hash_license_key(license_key),
            tier=UserTier.PRO,
            order_id=event["order_id"] or None,
            customer_email=event.get("customer_email"),
        )
        await db.commit()
        log.info("license_issued", order_id=event["order_id"], license_key_prefix=_mask(license_key))
        # Returned once so the store operator can deliver it (LS webhook log);
        # only the hash is stored server-side.
        return {"status": "ok", "license_key": license_key}

    return {"status": "ignored"}
