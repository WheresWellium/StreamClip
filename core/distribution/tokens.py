"""Encrypt/decrypt OAuth and app secrets at rest."""

from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet, InvalidToken

from core.config import get_settings
from core.errors import StreamClipError


def _fernet() -> Fernet:
    raw = get_settings().distribution.token_encryption_key
    if not raw:
        raise StreamClipError(
            "DISTRIBUTION_TOKEN_KEY not configured",
            user_message="Distribution encryption is not configured on this install.",
            code="distribution_not_configured",
            http_status=503,
        )
    try:
        key = raw.encode() if isinstance(raw, str) else raw
        return Fernet(key)
    except (ValueError, TypeError) as exc:
        raise StreamClipError(
            "Invalid DISTRIBUTION_TOKEN_KEY",
            user_message="Distribution encryption key is invalid.",
            code="distribution_not_configured",
            http_status=503,
        ) from exc


def encrypt_secret(plain: str) -> str:
    if not plain:
        return ""
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_secret(cipher: str) -> str:
    if not cipher:
        return ""
    try:
        return _fernet().decrypt(cipher.encode()).decode()
    except InvalidToken as exc:
        raise StreamClipError(
            "Failed to decrypt stored secret",
            user_message="Stored credentials could not be decrypted. Reconnect the platform.",
            code="token_decrypt_failed",
        ) from exc


def generate_token_key() -> str:
    return Fernet.generate_key().decode()


def is_token_key_configured() -> bool:
    return bool(get_settings().distribution.token_encryption_key.strip())
