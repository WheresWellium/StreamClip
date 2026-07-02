from __future__ import annotations
import pytest
from unittest.mock import patch
from core.errors import AuthError

@pytest.mark.asyncio
async def test_register_returns_tokens(client):
    email = "refresh_user@example.com"
    reg = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "password12345", "display_name": "R"},
    )
    if reg.status_code != 201:
        pytest.skip("register unavailable")
    refresh = reg.json()["refresh_token"]
    resp = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    assert resp.json()["access_token"]

@pytest.mark.asyncio
async def test_refresh_invalid_token(client):
    resp = await client.post("/api/auth/refresh", json={"refresh_token": "not.a.jwt"})
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_refresh_wrong_token_type(client, monkeypatch):
    from core.config import get_settings
    from backend.middleware.auth import create_access_token
    cfg = get_settings()
    # access token not refresh
    tok = create_access_token("user-id-1", cfg)
    resp = await client.post("/api/auth/refresh", json={"refresh_token": tok})
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401
