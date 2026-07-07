"""Unit tests for OAuth state, credential resolution, and connection persistence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.config import get_settings
from core.distribution import connections as conn_mod
from core.distribution import credentials as cred_mod
from core.distribution import oauth_state as oauth_mod
from core.distribution.base import PlatformCredentials
from core.distribution.tokens import encrypt_secret, generate_token_key
from core.errors import StreamClipError


@pytest.fixture
def token_key(monkeypatch):
    key = generate_token_key()
    cfg = get_settings(reload=True)
    old = cfg.distribution.token_encryption_key
    cfg.distribution.token_encryption_key = key
    yield key
    cfg.distribution.token_encryption_key = old


def test_oauth_state_roundtrip():
    cfg = get_settings(reload=True)
    state = oauth_mod.create_oauth_state("user-1", "youtube_shorts", cfg)
    user_id = oauth_mod.verify_oauth_state(state, "youtube_shorts", cfg)
    assert user_id == "user-1"


def test_oauth_state_rejects_wrong_platform():
    cfg = get_settings(reload=True)
    state = oauth_mod.create_oauth_state("user-1", "youtube_shorts", cfg)
    with pytest.raises(StreamClipError) as exc:
        oauth_mod.verify_oauth_state(state, "tiktok", cfg)
    assert exc.value.code == "oauth_state_invalid"


def test_oauth_state_rejects_tampered_token():
    cfg = get_settings(reload=True)
    with pytest.raises(StreamClipError):
        oauth_mod.verify_oauth_state("not-a-jwt", "youtube_shorts", cfg)


def test_default_redirect_uri():
    cfg = get_settings(reload=True)
    cfg.distribution.web_origin = "https://clip.example.com"
    uri = cred_mod.default_redirect_uri("youtube_shorts", cfg)
    assert uri.endswith("/api/distribution/oauth/youtube_shorts/callback")


@pytest.mark.asyncio
async def test_resolve_oauth_app_from_db_row(token_key):
    row = SimpleNamespace(
        client_id="cid",
        client_secret_enc=encrypt_secret("secret"),
        redirect_uri="http://custom/cb",
    )
    db = AsyncMock()
    repo = MagicMock()
    repo.get = AsyncMock(return_value=row)

    with patch.object(cred_mod, "InstallOAuthAppRepository", return_value=repo):
        creds = await cred_mod.resolve_oauth_app(db, "youtube_shorts")

    assert creds.client_id == "cid"
    assert creds.client_secret == "secret"
    assert creds.redirect_uri == "http://custom/cb"


@pytest.mark.asyncio
async def test_resolve_oauth_app_managed_mode(monkeypatch):
    cfg = get_settings(reload=True)
    cfg.distribution.mode = "managed"
    cfg.distribution.youtube_client_id = "yt-id"
    cfg.distribution.youtube_client_secret = "yt-sec"
    db = AsyncMock()

    creds = await cred_mod.resolve_oauth_app(db, "youtube_shorts", cfg=cfg)
    assert creds.client_id == "yt-id"
    assert creds.client_secret == "yt-sec"


@pytest.mark.asyncio
async def test_resolve_oauth_app_not_configured():
    cfg = get_settings(reload=True)
    cfg.distribution.mode = "byo"
    db = AsyncMock()
    repo = MagicMock()
    repo.get = AsyncMock(return_value=None)

    with patch.object(cred_mod, "InstallOAuthAppRepository", return_value=repo):
        with pytest.raises(StreamClipError) as exc:
            await cred_mod.resolve_oauth_app(db, "youtube_shorts", cfg=cfg)
    assert exc.value.code == "oauth_not_configured"


@pytest.mark.asyncio
async def test_save_platform_connection(token_key):
    repo = MagicMock()
    repo.upsert_tokens = AsyncMock()
    db = AsyncMock()

    creds = PlatformCredentials(
        platform_id="youtube_shorts",
        access_token="access",
        refresh_token="refresh",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    with patch.object(conn_mod, "PlatformConnectionRepository", return_value=repo):
        await conn_mod.save_platform_connection(
            db,
            user_id="u1",
            platform="youtube_shorts",
            account_label="Channel",
            credentials=creds,
        )

    repo.upsert_tokens.assert_awaited()


def test_connection_to_credentials_roundtrip(token_key):
    connection = SimpleNamespace(
        platform="youtube_shorts",
        access_token_enc=encrypt_secret("at"),
        refresh_token_enc=encrypt_secret("rt"),
        token_expires_at=datetime.now(timezone.utc),
    )
    creds = conn_mod.connection_to_credentials(connection)
    assert creds.access_token == "at"
    assert creds.refresh_token == "rt"


@pytest.mark.asyncio
async def test_ensure_fresh_credentials_refreshes_expired(token_key):
    expired = datetime.now(timezone.utc) - timedelta(hours=1)
    connection = SimpleNamespace(
        platform="youtube_shorts",
        user_id="u1",
        account_label="Ch",
        access_token_enc=encrypt_secret("old"),
        refresh_token_enc=encrypt_secret("rt"),
        token_expires_at=expired,
        metadata_json={},
    )
    refreshed = PlatformCredentials(
        platform_id="youtube_shorts",
        access_token="new",
        refresh_token="rt",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    adapter = MagicMock()
    adapter.refresh_token = AsyncMock(return_value=refreshed)
    repo = MagicMock()
    repo.upsert_tokens = AsyncMock()
    db = AsyncMock()

    with patch.object(conn_mod, "build_adapter", AsyncMock(return_value=adapter)), \
         patch.object(conn_mod, "PlatformConnectionRepository", return_value=repo):
        out = await conn_mod.ensure_fresh_credentials(db, connection)

    assert out.access_token == "new"
    repo.upsert_tokens.assert_awaited()


@pytest.mark.asyncio
async def test_ensure_fresh_credentials_expired_without_refresh(token_key):
    expired = datetime.now(timezone.utc) - timedelta(hours=1)
    connection = SimpleNamespace(
        platform="youtube_shorts",
        user_id="u1",
        account_label="Ch",
        access_token_enc=encrypt_secret("old"),
        refresh_token_enc=None,
        token_expires_at=expired,
        metadata_json={},
    )
    db = AsyncMock()
    with pytest.raises(StreamClipError) as exc:
        await conn_mod.ensure_fresh_credentials(db, connection)
    assert exc.value.code == "TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_ensure_fresh_credentials_missing_access_token(token_key):
    connection = SimpleNamespace(
        platform="youtube_shorts",
        user_id="u1",
        account_label="Ch",
        access_token_enc=encrypt_secret(""),
        refresh_token_enc=None,
        token_expires_at=None,
        metadata_json={},
    )
    from core.distribution.errors import NoConnectionError

    db = AsyncMock()
    with pytest.raises(NoConnectionError):
        await conn_mod.ensure_fresh_credentials(db, connection)


@pytest.mark.asyncio
async def test_resolve_oauth_app_managed_missing_env(monkeypatch):
    cfg = get_settings(reload=True)
    cfg.distribution.mode = "managed"
    cfg.distribution.youtube_client_id = ""
    cfg.distribution.youtube_client_secret = ""
    db = AsyncMock()

    with pytest.raises(StreamClipError) as exc:
        await cred_mod.resolve_oauth_app(db, "youtube_shorts", cfg=cfg)
    assert exc.value.code == "oauth_not_configured"


@pytest.mark.asyncio
async def test_ensure_fresh_credentials_returns_valid(token_key):
    future = datetime.now(timezone.utc) + timedelta(hours=2)
    connection = SimpleNamespace(
        platform="youtube_shorts",
        user_id="u1",
        account_label="Ch",
        access_token_enc=encrypt_secret("valid"),
        refresh_token_enc=None,
        token_expires_at=future,
        metadata_json={},
    )
    db = AsyncMock()
    out = await conn_mod.ensure_fresh_credentials(db, connection)
    assert out.access_token == "valid"
