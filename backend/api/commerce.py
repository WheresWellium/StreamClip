"""Lemon Squeezy webhook handler for license delivery."""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from core.commerce.lemon_squeezy import parse_order_event, verify_webhook_signature
from core.config import get_settings

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/commerce", tags=["commerce"])


@router.post("/webhooks/lemon-squeezy", status_code=status.HTTP_200_OK)
async def lemon_squeezy_webhook(
    request: Request,
    x_signature: Annotated[str | None, Header(alias="X-Signature")] = None,
) -> dict:
    cfg = get_settings()
    body = await request.body()
    secret = cfg.commerce.lemon_squeezy_webhook_secret
    if secret and not verify_webhook_signature(body, x_signature or "", secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    import json

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
    if event["event_name"] == "order_created":
        log.info("license_generated", license_key_prefix=event["license_key"][:12])
    return {"status": "ok", "license_key": event.get("license_key")}
