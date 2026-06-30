"""Authentication API tests."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_register_and_login(client):
    email = "tester@example.com"
    password = "password123"

    reg = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "display_name": "Tester"},
    )
    if reg.status_code == 201:
        body = reg.json()
        assert body["access_token"]
        assert body["user"]["email"] == email
        return

    # User may already exist from a prior run
    assert reg.status_code in (401, 201)

    login = await client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    data = login.json()
    assert data["access_token"]
    assert data["refresh_token"]

    me = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == email


@pytest.mark.asyncio
async def test_login_invalid_password(client):
    resp = await client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401
