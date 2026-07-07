"""Auth claim-device and refresh error paths."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

import backend.api.auth as auth_api
from backend.db.session import get_db
from backend.middleware.auth import get_current_user_id, get_device_id, require_user_id
from core.errors import AuthError

USER = "auth-user-1"


@pytest.fixture
def auth_client(app, client, monkeypatch):
    session = MagicMock()
    session.commit = AsyncMock()

    async def fake_db():
        yield session

    repo = MagicMock()
    repo.claim_for_user = AsyncMock(return_value=2)
    monkeypatch.setattr(auth_api, "DeviceRepository", lambda db: repo)

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[require_user_id] = lambda: USER
    yield client, repo, session
    for dep in (get_db, require_user_id, get_device_id):
        app.dependency_overrides.pop(dep, None)


@pytest.mark.asyncio
async def test_claim_device_from_body(auth_client):
    client, repo, session = auth_client
    resp = await client.post(
        "/api/auth/claim-device",
        json={"device_id": "device-claim01"},
    )
    assert resp.status_code == 200
    assert resp.json()["jobs_claimed"] == 2
    repo.claim_for_user.assert_awaited_with("device-claim01", USER)
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_claim_device_requires_id(auth_client, app):
    client, _, _ = auth_client
    app.dependency_overrides[get_device_id] = lambda: None
    resp = await client.post("/api/auth/claim-device", json={})
    app.dependency_overrides.pop(get_device_id, None)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_refresh_invalid_token_type(auth_client, monkeypatch):
    client, _, _ = auth_client

    class FakeAuth:
        def __init__(self, db, cfg) -> None:
            pass

    monkeypatch.setattr(auth_api, "AuthService", FakeAuth)
    monkeypatch.setattr(
        auth_api,
        "decode_token",
        lambda token, cfg: {"type": "access", "sub": USER},
    )
    resp = await client.post("/api/auth/refresh", json={"refresh_token": "tok"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_decode_failure(auth_client, monkeypatch):
    client, _, _ = auth_client

    def fail_decode(token, cfg):
        raise AuthError("bad token")

    monkeypatch.setattr(auth_api, "decode_token", fail_decode)
    resp = await client.post("/api/auth/refresh", json={"refresh_token": "tok"})
    assert resp.status_code == 401
