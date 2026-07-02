"""Stripe billing webhook stub."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Request

from core.billing import handle_stripe_webhook_stub

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request) -> dict[str, str]:
    """Accept Stripe events when billing is enabled (stub)."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    action = handle_stripe_webhook_stub(payload)
    return {"status": "ok", "action": action}
