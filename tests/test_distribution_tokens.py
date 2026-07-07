"""OAuth secret encryption at rest."""

from __future__ import annotations

import pytest

from core.config import get_settings
from core.distribution import tokens
from core.errors import StreamClipError


@pytest.fixture
def token_key(monkeypatch):
    key = tokens.generate_token_key()
    cfg = get_settings(reload=True)
    old = cfg.distribution.token_encryption_key
    cfg.distribution.token_encryption_key = key
    yield key
    cfg.distribution.token_encryption_key = old


def test_encrypt_decrypt_roundtrip(token_key):
    cipher = tokens.encrypt_secret("client-secret-123")
    assert tokens.decrypt_secret(cipher) == "client-secret-123"


def test_empty_secret_passthrough(token_key):
    assert tokens.encrypt_secret("") == ""
    assert tokens.decrypt_secret("") == ""


def test_decrypt_invalid_cipher(token_key):
    with pytest.raises(StreamClipError) as exc:
        tokens.decrypt_secret("not-valid-fernet")
    assert exc.value.code == "token_decrypt_failed"


def test_fernet_missing_key(monkeypatch):
    cfg = get_settings(reload=True)
    cfg.distribution.token_encryption_key = ""
    with pytest.raises(StreamClipError) as exc:
        tokens.encrypt_secret("x")
    assert exc.value.code == "distribution_not_configured"


def test_fernet_invalid_key(monkeypatch):
    cfg = get_settings(reload=True)
    cfg.distribution.token_encryption_key = "not-a-fernet-key"
    with pytest.raises(StreamClipError) as exc:
        tokens.encrypt_secret("x")
    assert exc.value.http_status == 503


def test_generate_and_is_configured(token_key):
    assert tokens.is_token_key_configured() is True
    assert len(tokens.generate_token_key()) > 20
