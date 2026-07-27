"""Self-hosted license activation and entitlement verification.

A purchase is perpetual, but the *token* that proves it is deliberately
short-lived. The install renews it against the issuing records while the
license is still valid, so revoking a key stops working within one renewal
window instead of remaining valid for the life of the JWT.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt

from backend.db.models import UserTier
from core.config import Settings, get_settings


@dataclass(frozen=True)
class Entitlement:
    tier: UserTier
    machine_id: str
    expires_at: datetime | None
    license_key_hash: str
    # Absolute end of the purchase (None = perpetual). Distinct from the
    # token's own `exp`, which is only the re-verification deadline.
    license_expires_at: datetime | None = None
    token_id: str = ""


def hash_license_key(license_key: str) -> str:
    return hashlib.sha256(license_key.strip().encode("utf-8")).hexdigest()


# One-time purchases promise a perpetual entitlement (MASTER_TODO §8.6).
# JWT requires a numeric exp, so "perpetual" is a 100-year horizon on the
# licence itself; the token still expires on the renewal window below.
PERPETUAL_DAYS = 36500


def renewal_window_days(cfg: Settings) -> int:
    """How long a token stays usable before the install must re-verify.

    Mirrors the offline grace period: a user can stay offline that long and
    keep working, but a revoked key cannot outlive the window.
    """
    return max(1, int(cfg.licensing.offline_grace_days))


def create_entitlement_token(
    *,
    tier: UserTier,
    machine_id: str,
    license_key_hash: str,
    expires_at: datetime | None,
    cfg: Settings | None = None,
) -> str:
    cfg = cfg or get_settings()
    now = datetime.now(timezone.utc)
    license_exp = expires_at or (now + timedelta(days=PERPETUAL_DAYS))
    # The token expires at the renewal deadline, never past the licence end.
    token_exp = min(license_exp, now + timedelta(days=renewal_window_days(cfg)))
    payload = {
        "type": "entitlement",
        "tier": tier.value,
        "machine_id": machine_id,
        "license_key_hash": license_key_hash,
        "license_exp": int(license_exp.timestamp()),
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": token_exp,
    }
    return jwt.encode(payload, cfg.auth.secret_key, algorithm=cfg.auth.algorithm)


def verify_entitlement_token(token: str, *, machine_id: str, cfg: Settings | None = None) -> Entitlement:
    cfg = cfg or get_settings()
    try:
        payload = jwt.decode(token, cfg.auth.secret_key, algorithms=[cfg.auth.algorithm])
    except jwt.InvalidTokenError as exc:
        raise ValueError("Invalid or expired license") from exc
    if payload.get("type") != "entitlement":
        raise ValueError("Wrong token type")
    if payload.get("machine_id") != machine_id:
        raise ValueError("License bound to a different machine")
    exp = payload.get("exp")
    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc) if exp else None
    license_exp = payload.get("license_exp")
    license_expires_at = (
        datetime.fromtimestamp(license_exp, tz=timezone.utc) if license_exp else None
    )
    return Entitlement(
        tier=UserTier(payload["tier"]),
        machine_id=machine_id,
        expires_at=expires_at,
        license_key_hash=payload["license_key_hash"],
        license_expires_at=license_expires_at,
        token_id=str(payload.get("jti") or ""),
    )


def activate_license_key(
    license_key: str,
    machine_id: str,
    *,
    tier: UserTier,
    cfg: Settings | None = None,
) -> tuple[str, Entitlement]:
    """Issue a signed entitlement JWT for a key already verified against
    the issued-license records (see backend/api/license.py)."""
    cfg = cfg or get_settings()
    key = license_key.strip()
    if len(key) < 16:
        raise ValueError("Invalid license key")
    key_hash = hash_license_key(key)
    # entitlement_days == 0 → perpetual (one-time purchase product promise)
    days = cfg.licensing.entitlement_days
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=days) if days > 0 else None
    )
    token = create_entitlement_token(
        tier=tier,
        machine_id=machine_id,
        license_key_hash=key_hash,
        expires_at=expires_at,
        cfg=cfg,
    )
    entitlement = verify_entitlement_token(token, machine_id=machine_id, cfg=cfg)
    persist_entitlement_token(token, cfg)
    return token, entitlement


def persist_entitlement_token(token: str, cfg: Settings | None = None) -> None:
    """Write the entitlement token this install should present from now on."""
    cfg = cfg or get_settings()
    path = cfg.licensing.license_file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"entitlement_jwt": token}, indent=2), encoding="utf-8")


# Retained for existing callers/tests that import the original private name.
_persist_license_file = persist_entitlement_token


def load_persisted_entitlement(cfg: Settings | None = None) -> str | None:
    cfg = cfg or get_settings()
    path = cfg.licensing.license_file
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data.get("entitlement_jwt")


def clear_persisted_entitlement(cfg: Settings | None = None) -> None:
    """Drop the local token so a revoked install falls back to FREE at once."""
    cfg = cfg or get_settings()
    path = cfg.licensing.license_file
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def license_is_perpetual(entitlement: Entitlement) -> bool:
    """True when the purchase has no real end date (one-time purchase)."""
    if entitlement.license_expires_at is None:
        return True
    horizon = datetime.now(timezone.utc) + timedelta(days=PERPETUAL_DAYS - 365)
    return entitlement.license_expires_at > horizon


def get_install_tier(machine_id: str, cfg: Settings | None = None) -> UserTier:
    cfg = cfg or get_settings()
    if not cfg.licensing.enabled:
        return UserTier.FREE
    token = load_persisted_entitlement(cfg)
    if not token:
        return UserTier.FREE
    try:
        return verify_entitlement_token(token, machine_id=machine_id, cfg=cfg).tier
    except ValueError:
        return UserTier.FREE
