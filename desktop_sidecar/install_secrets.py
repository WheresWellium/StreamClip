"""Per-install auth and distribution secrets for packaged desktop (W3)."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

import structlog
from cryptography.fernet import Fernet

log = structlog.get_logger(__name__)

_SECRETS_FILE = "secrets.json"
_AUTH_ENV = "STREAMCLIP_AUTH__SECRET_KEY"
_DIST_ENV = "STREAMCLIP_DISTRIBUTION__TOKEN_ENCRYPTION_KEY"


def _generate_secrets() -> dict[str, str]:
    return {
        "auth_secret_key": secrets.token_urlsafe(32),
        "token_encryption_key": Fernet.generate_key().decode("ascii"),
    }


def _load_secrets(path: Path) -> dict[str, str] | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("install_secrets_read_failed", path=str(path), error=str(exc))
        return None
    if not isinstance(raw, dict):
        log.warning("install_secrets_invalid_shape", path=str(path))
        return None
    auth = raw.get("auth_secret_key")
    token = raw.get("token_encryption_key")
    if not isinstance(auth, str) or not auth.strip():
        log.warning("install_secrets_missing_auth", path=str(path))
        return None
    if not isinstance(token, str) or not token.strip():
        log.warning("install_secrets_missing_token", path=str(path))
        return None
    return {"auth_secret_key": auth.strip(), "token_encryption_key": token.strip()}


def _persist_secrets(path: Path, payload: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def ensure_install_secrets(data_dir: Path) -> None:
    """Create or load per-install secrets and export via os.environ.setdefault."""
    secrets_path = data_dir / _SECRETS_FILE
    payload = _load_secrets(secrets_path) if secrets_path.is_file() else None
    if payload is None:
        payload = _generate_secrets()
        try:
            _persist_secrets(secrets_path, payload)
            log.info("install_secrets_created", path=str(secrets_path))
        except OSError as exc:
            log.warning("install_secrets_write_failed", path=str(secrets_path), error=str(exc))
            # Still export generated values for this boot even if persist failed.
    os.environ.setdefault(_AUTH_ENV, payload["auth_secret_key"])
    os.environ.setdefault(_DIST_ENV, payload["token_encryption_key"])
