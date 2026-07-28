"""Structlog processor: redact common secrets from log event dicts."""

from __future__ import annotations

from typing import Any, MutableMapping

# Case-insensitive exact or substring match against log keys.
_SENSITIVE_KEY_FRAGMENTS: tuple[str, ...] = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "entitlement_jwt",
    "license_key",
    "webhook_secret",
    "encryption_key",
    "smtp_password",
    "client_secret",
    "access_token",
    "refresh_token",
)

# Never treat these as sensitive wholesale (even if a fragment matched).
_PROTECTED_KEYS: frozenset[str] = frozenset({"error", "message"})

_REDACTED = "[redacted]"


def _key_is_sensitive(key: str) -> bool:
    lower = key.lower()
    if lower in _PROTECTED_KEYS:
        return False
    return any(fragment in lower for fragment in _SENSITIVE_KEY_FRAGMENTS)


def _redact_mapping(mapping: MutableMapping[str, Any]) -> None:
    for key in list(mapping.keys()):
        if _key_is_sensitive(key):
            mapping[key] = _REDACTED


def redact_log_event(
    logger: Any,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Structlog processor: redact sensitive keys in ``event_dict``.

    Redacts matching top-level keys, then one level of nested dict values
    when those nested keys match. Does not redact keys named ``error`` or
    ``message``.
    """
    _redact_mapping(event_dict)
    for key, value in list(event_dict.items()):
        if isinstance(value, dict) and not _key_is_sensitive(key):
            _redact_mapping(value)
    return event_dict
