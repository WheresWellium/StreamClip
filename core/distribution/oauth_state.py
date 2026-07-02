"""Signed OAuth state (CSRF protection)."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import jwt

from core.config import Settings, get_settings
from core.errors import StreamClipError


def create_oauth_state(user_id: str, platform: str, cfg: Settings | None = None) -> str:
    cfg = cfg or get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "type": "oauth_state",
        "sub": user_id,
        "platform": platform,
        "nonce": secrets.token_urlsafe(16),
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }
    return jwt.encode(payload, cfg.auth.secret_key, algorithm=cfg.auth.algorithm)


def verify_oauth_state(token: str, platform: str, cfg: Settings | None = None) -> str:
    cfg = cfg or get_settings()
    try:
        payload = jwt.decode(token, cfg.auth.secret_key, algorithms=[cfg.auth.algorithm])
    except jwt.InvalidTokenError as exc:
        raise StreamClipError(
            "Invalid OAuth state",
            user_message="Connection expired or was tampered with. Try again.",
            code="oauth_state_invalid",
        ) from exc
    if payload.get("type") != "oauth_state":
        raise StreamClipError("Invalid OAuth state", code="oauth_state_invalid")
    if payload.get("platform") != platform:
        raise StreamClipError("OAuth platform mismatch", code="oauth_state_invalid")
    user_id = payload.get("sub")
    if not user_id:
        raise StreamClipError("OAuth state missing user", code="oauth_state_invalid")
    return str(user_id)
