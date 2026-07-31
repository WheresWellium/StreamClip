"""Self-hosted license activation and entitlement verification."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jwt
import structlog

from backend.db.models import UserTier
from core.config import Settings, get_settings, user_data_root

log = structlog.get_logger(__name__)

# Redis / in-process set of revoked license_key_hash values. Checking the hash
# (not only jti) invalidates every entitlement JWT ever issued for that key.
REVOKED_LICENSE_HASHES_KEY = "streamclip:revoked_license_hashes"


@dataclass(frozen=True)
class Entitlement:
    tier: UserTier
    machine_id: str
    expires_at: datetime | None
    license_key_hash: str


def hash_license_key(license_key: str) -> str:
    return hashlib.sha256(license_key.strip().encode("utf-8")).hexdigest()


# One-time purchases promise a perpetual entitlement (MASTER_TODO §8.6).
# JWT requires a numeric exp, so "perpetual" is a 100-year horizon.
PERPETUAL_DAYS = 36500


def revoke_entitlement_hash(license_key_hash: str) -> None:
    """Block future verify_entitlement_token calls for this license hash."""
    try:
        from core.celery_app import get_redis

        get_redis().sadd(REVOKED_LICENSE_HASHES_KEY, license_key_hash)
    except Exception as exc:
        log.warning(
            "entitlement_blocklist_write_failed",
            hash_prefix=license_key_hash[:12],
            error=str(exc),
        )


def is_entitlement_hash_revoked(license_key_hash: str) -> bool:
    try:
        from core.celery_app import get_redis

        return bool(get_redis().sismember(REVOKED_LICENSE_HASHES_KEY, license_key_hash))
    except Exception as exc:
        # Fail-open so a Redis blip does not lock every install; revoke still
        # downgrades DB tier for authenticated API paths.
        log.warning(
            "entitlement_blocklist_read_failed",
            hash_prefix=license_key_hash[:12],
            error=str(exc),
        )
        return False


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
    exp = expires_at or (now + timedelta(days=PERPETUAL_DAYS))
    payload = {
        "type": "entitlement",
        "tier": tier.value,
        "machine_id": machine_id,
        "license_key_hash": license_key_hash,
        "iat": now,
        "exp": exp,
        "jti": uuid.uuid4().hex,
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
    key_hash = str(payload.get("license_key_hash") or "")
    if key_hash and is_entitlement_hash_revoked(key_hash):
        raise ValueError("License has been revoked")
    exp = payload.get("exp")
    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc) if exp else None
    return Entitlement(
        tier=UserTier(payload["tier"]),
        machine_id=machine_id,
        expires_at=expires_at,
        license_key_hash=key_hash,
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
    _persist_license_file(token, cfg)
    return token, entitlement


def _persist_license_file(token: str, cfg: Settings) -> None:
    payload = json.dumps({"entitlement_jwt": token}, indent=2)
    path = cfg.licensing.license_file
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
        return
    except OSError as exc:
        # Packaged installs can land in a read-only prefix (e.g. Program Files),
        # which would otherwise turn a valid activation into a 500. Relocate the
        # license file into the per-user data root and remember it for this run.
        fallback = (user_data_root() / path.name).resolve()
        if fallback == path.resolve():
            raise
        try:
            fallback.parent.mkdir(parents=True, exist_ok=True)
            fallback.write_text(payload, encoding="utf-8")
        except OSError:
            raise exc from None
        cfg.licensing.license_file = fallback
        log.warning(
            "license_file_relocated",
            attempted=str(path),
            fallback=str(fallback),
        )


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
    cfg = cfg or get_settings()
    try:
        cfg.licensing.license_file.unlink(missing_ok=True)
    except OSError:
        return


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
