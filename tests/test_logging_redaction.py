"""Focused tests for structlog secret redaction (no desktop mark)."""

from __future__ import annotations

from core.logging_redact import redact_log_event


def test_redacts_sensitive_top_level_keys():
    event = {
        "event": "login",
        "password": "hunter2",
        "api_key": "sk-abc",
        "Authorization": "Bearer xyz",
        "user_id": 42,
    }
    out = redact_log_event(None, "info", event)
    assert out["password"] == "[redacted]"
    assert out["api_key"] == "[redacted]"
    assert out["Authorization"] == "[redacted]"
    assert out["user_id"] == 42
    assert out["event"] == "login"


def test_redacts_case_insensitive_substring_keys():
    event = {
        "SMTP_PASSWORD": "mail-secret",
        "my_access_token": "tok",
        "webhook_secret_value": "whsec",
        "clientSecret": "cs",
        "entitlement_jwt": "eyJ...",
        "license_key": "lic-1",
        "encryption_key": "ek",
        "refresh_token": "rt",
        "apikey": "k",
        "token": "t",
        "secret": "s",
    }
    out = redact_log_event(None, "warning", event)
    for key in event:
        assert out[key] == "[redacted]", key


def test_redacts_nested_dict_one_level():
    event = {
        "event": "oauth",
        "creds": {
            "access_token": "at",
            "refresh_token": "rt",
            "username": "alice",
        },
        "ok": True,
    }
    out = redact_log_event(None, "info", event)
    assert out["creds"]["access_token"] == "[redacted]"
    assert out["creds"]["refresh_token"] == "[redacted]"
    assert out["creds"]["username"] == "alice"
    assert out["ok"] is True


def test_does_not_redact_deeper_than_one_nested_level():
    event = {
        "payload": {
            "inner": {
                "password": "still-visible",
            }
        }
    }
    out = redact_log_event(None, "info", event)
    assert out["payload"]["inner"]["password"] == "still-visible"


def test_does_not_redact_error_or_message_keys():
    event = {
        "error": "password validation failed",
        "message": "token refresh retry",
        "Error": "auth boom",
        "MESSAGE": "ok",
        "password": "secret",
    }
    out = redact_log_event(None, "error", event)
    assert out["error"] == "password validation failed"
    assert out["message"] == "token refresh retry"
    assert out["Error"] == "auth boom"
    assert out["MESSAGE"] == "ok"
    assert out["password"] == "[redacted]"


def test_sensitive_top_level_dict_value_replaced_wholesale():
    event = {
        "client_secret": {"nested": "value"},
        "meta": {"token": "t", "id": 1},
    }
    out = redact_log_event(None, "info", event)
    assert out["client_secret"] == "[redacted]"
    assert out["meta"]["token"] == "[redacted]"
    assert out["meta"]["id"] == 1
