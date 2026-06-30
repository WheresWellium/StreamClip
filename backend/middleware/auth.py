"""
StreamClip — Authentication

Two-tier auth:
  • Anonymous mode  — for local dev. Every request gets owner_id=None.
  • JWT bearer mode — for production. Tokens issued by /api/auth/login.

The dependency `get_current_user_id()` returns the user ID or None. Route
handlers that allow anonymous use can accept None; routes that require a
user wrap the dependency in `require_user_id()`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
import structlog
from fastapi import Depends, Header, HTTPException, status
from passlib.context import CryptContext

from core.config import Settings, get_settings
from core.errors import AuthError

log = structlog.get_logger(__name__)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── Password hashing ────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ─── JWT issuing / verification ──────────────────────────────────────────────

def create_access_token(user_id: str, cfg: Settings | None = None) -> str:
    cfg = cfg or get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=cfg.auth.access_token_expire_minutes),
        "type": "access",
    }
    return jwt.encode(payload, cfg.auth.secret_key, algorithm=cfg.auth.algorithm)


def create_refresh_token(user_id: str, cfg: Settings | None = None) -> str:
    cfg = cfg or get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(days=cfg.auth.refresh_token_expire_days),
        "type": "refresh",
    }
    return jwt.encode(payload, cfg.auth.secret_key, algorithm=cfg.auth.algorithm)


def decode_token(token: str, cfg: Settings | None = None) -> dict:
    cfg = cfg or get_settings()
    try:
        return jwt.decode(token, cfg.auth.secret_key, algorithms=[cfg.auth.algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Invalid token") from exc


# ─── FastAPI dependencies ────────────────────────────────────────────────────

async def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
) -> str | None:
    """
    Returns the user_id from the Authorization header, or None if anonymous
    mode is enabled and no header is present.
    """
    cfg = get_settings()

    if authorization is None:
        if cfg.auth.allow_anonymous:
            return None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be 'Bearer <token>'",
        )

    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token, cfg)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=exc.user_message)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong token type",
        )
    return payload["sub"]


async def require_user_id(
    user_id: Annotated[str | None, Depends(get_current_user_id)],
) -> str:
    """Like get_current_user_id but rejects anonymous requests."""
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user_id
