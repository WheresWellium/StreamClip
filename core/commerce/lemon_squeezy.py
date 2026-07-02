"""Lemon Squeezy commerce integration."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

from core.licensing import hash_license_key


def generate_license_key(prefix: str = "SCPRO") -> str:
    body = secrets.token_hex(8).upper()
    return f"{prefix}-{body[0:4]}-{body[4:8]}-{body[8:12]}-{body[12:16]}"


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


def parse_order_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract license-relevant fields from a Lemon Squeezy webhook payload."""
    meta = payload.get("meta", {})
    data = payload.get("data", {})
    attrs = data.get("attributes", {})
    license_key = generate_license_key()
    return {
        "event_name": meta.get("event_name", ""),
        "order_id": str(data.get("id", "")),
        "customer_email": attrs.get("user_email") or attrs.get("customer_email"),
        "product_name": attrs.get("first_order_item", {}).get("product_name")
        if isinstance(attrs.get("first_order_item"), dict)
        else attrs.get("product_name"),
        "license_key": license_key,
        "license_key_hash": hash_license_key(license_key),
    }
