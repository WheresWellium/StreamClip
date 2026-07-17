"""Lemon Squeezy License API client for self-hosted activation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

LS_LICENSE_ACTIVATE_URL = "https://api.lemonsqueezy.com/v1/licenses/activate"
LS_LICENSE_VALIDATE_URL = "https://api.lemonsqueezy.com/v1/licenses/validate"
DEFAULT_TIMEOUT_S = 10.0


@dataclass(frozen=True)
class LSActivateResult:
    ok: bool
    error: str | None = None
    variant_id: str = ""
    order_id: str = ""
    customer_email: str | None = None
    instance_id: str | None = None
    license_status: str = ""


@dataclass(frozen=True)
class LSValidateResult:
    ok: bool
    error: str | None = None
    license_status: str = ""


def _parse_meta(payload: dict[str, Any]) -> dict[str, Any]:
    meta = payload.get("meta")
    return meta if isinstance(meta, dict) else {}


async def activate_license_with_ls(
    license_key: str,
    instance_name: str,
    *,
    api_key: str,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> LSActivateResult:
    """Activate a license key against Lemon Squeezy (binds instance_name)."""
    if not api_key:
        return LSActivateResult(ok=False, error="api_key_unconfigured")
    body = urlencode(
        {
            "license_key": license_key.strip(),
            "instance_name": instance_name.strip(),
        },
    )
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Bearer {api_key}",
    }
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(LS_LICENSE_ACTIVATE_URL, content=body, headers=headers)
    except httpx.HTTPError as exc:
        return LSActivateResult(ok=False, error=f"transport_error:{exc}")

    try:
        payload = resp.json()
    except ValueError:
        return LSActivateResult(ok=False, error=f"invalid_json:{resp.status_code}")

    if not isinstance(payload, dict):
        return LSActivateResult(ok=False, error="invalid_response")

    if not payload.get("activated"):
        err = payload.get("error")
        return LSActivateResult(ok=False, error=str(err or "activation_failed"))

    meta = _parse_meta(payload)
    license_key_obj = payload.get("license_key")
    status = ""
    if isinstance(license_key_obj, dict):
        status = str(license_key_obj.get("status") or "")

    instance = payload.get("instance")
    instance_id = None
    if isinstance(instance, dict):
        instance_id = str(instance.get("id") or "") or None

    return LSActivateResult(
        ok=True,
        variant_id=str(meta.get("variant_id") or ""),
        order_id=str(meta.get("order_id") or ""),
        customer_email=meta.get("customer_email"),
        instance_id=instance_id,
        license_status=status,
    )


async def validate_license_with_ls(
    license_key: str,
    instance_id: str,
    *,
    api_key: str,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> LSValidateResult:
    """Validate an activated license key instance with Lemon Squeezy."""
    if not api_key:
        return LSValidateResult(ok=False, error="api_key_unconfigured")
    body = urlencode(
        {
            "license_key": license_key.strip(),
            "instance_id": instance_id.strip(),
        },
    )
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Bearer {api_key}",
    }
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(LS_LICENSE_VALIDATE_URL, content=body, headers=headers)
    except httpx.HTTPError as exc:
        return LSValidateResult(ok=False, error=f"transport_error:{exc}")

    try:
        payload = resp.json()
    except ValueError:
        return LSValidateResult(ok=False, error=f"invalid_json:{resp.status_code}")

    if not isinstance(payload, dict):
        return LSValidateResult(ok=False, error="invalid_response")

    if not payload.get("valid"):
        err = payload.get("error")
        return LSValidateResult(ok=False, error=str(err or "validation_failed"))

    license_key_obj = payload.get("license_key")
    status = ""
    if isinstance(license_key_obj, dict):
        status = str(license_key_obj.get("status") or "")

    return LSValidateResult(ok=True, license_status=status)
