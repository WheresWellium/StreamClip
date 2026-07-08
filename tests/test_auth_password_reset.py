"""Auth password reset, profile, and remember-me API tests."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.middleware.auth import decode_token
from core.config import get_settings


def _unique_email() -> str:
    return f"auth-{uuid.uuid4().hex[:10]}@example.com"


async def _register(client, email: str | None = None, password: str = "password12345") -> dict:
    email = email or _unique_email()
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "display_name": "Tester"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_forgot_password_always_returns_generic_message(client):
    with patch("backend.api.auth.send_password_reset_email") as email_task:
        resp = await client.post(
            "/api/auth/forgot-password",
            json={"email": "nobody-here@example.com"},
        )
    assert resp.status_code == 200
    assert "account exists" in resp.json()["message"].lower()
    email_task.delay.assert_not_called()


@pytest.mark.asyncio
async def test_forgot_password_enqueues_email_for_known_user(client):
    data = await _register(client)
    email = data["user"]["email"]
    fixed_token = "fixed-reset-token-for-tests-abc"

    with patch(
        "backend.services.auth_service.secrets.token_urlsafe",
        return_value=fixed_token,
    ), patch("backend.api.auth.send_password_reset_email") as email_task:
        resp = await client.post(
            "/api/auth/forgot-password",
            json={"email": email},
        )

    assert resp.status_code == 200
    email_task.delay.assert_called_once()
    args = email_task.delay.call_args[0]
    assert args[0] == email
    assert fixed_token in args[1]


@pytest.mark.asyncio
async def test_reset_password_and_login_with_new_password(client):
    data = await _register(client)
    email = data["user"]["email"]
    old_password = "password12345"
    new_password = "newpassword99"
    fixed_token = "reset-token-integration-test-value"

    with patch(
        "backend.services.auth_service.secrets.token_urlsafe",
        return_value=fixed_token,
    ), patch("backend.api.auth.send_password_reset_email"):
        await client.post("/api/auth/forgot-password", json={"email": email})

    reset = await client.post(
        "/api/auth/reset-password",
        json={"token": fixed_token, "new_password": new_password},
    )
    assert reset.status_code == 200

    old_login = await client.post(
        "/api/auth/login",
        json={"email": email, "password": old_password},
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/auth/login",
        json={"email": email, "password": new_password},
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_rejects_invalid_token(client):
    resp = await client.post(
        "/api/auth/reset-password",
        json={"token": "not-a-valid-reset-token", "new_password": "password12345"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_change_password_requires_auth(client):
    resp = await client.post(
        "/api/auth/change-password",
        json={"current_password": "old", "new_password": "newpassword1"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_change_password_updates_credentials(client):
    data = await _register(client)
    token = data["access_token"]
    email = data["user"]["email"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": "password12345", "new_password": "changedpass1"},
    )
    assert resp.status_code == 200

    assert (
        await client.post(
            "/api/auth/login",
            json={"email": email, "password": "password12345"},
        )
    ).status_code == 401
    assert (
        await client.post(
            "/api/auth/login",
            json={"email": email, "password": "changedpass1"},
        )
    ).status_code == 200


@pytest.mark.asyncio
async def test_update_profile_display_name(client):
    data = await _register(client)
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.patch(
        "/api/auth/me",
        headers=headers,
        json={"display_name": "Clip Captain"},
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Clip Captain"

    me = await client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["display_name"] == "Clip Captain"


@pytest.mark.asyncio
async def test_login_remember_me_false_sets_refresh_claim(client):
    data = await _register(client)
    email = data["user"]["email"]

    resp = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "password12345", "remember_me": False},
    )
    assert resp.status_code == 200
    payload = decode_token(resp.json()["refresh_token"], get_settings())
    assert payload.get("rem") is False


@pytest.mark.asyncio
async def test_refresh_preserves_remember_me_false(client):
    data = await _register(client)
    email = data["user"]["email"]

    login = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "password12345", "remember_me": False},
    )
    refresh_token = login.json()["refresh_token"]

    refreshed = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refreshed.status_code == 200
    payload = decode_token(refreshed.json()["refresh_token"], get_settings())
    assert payload.get("rem") is False


@pytest.mark.asyncio
async def test_create_password_reset_skips_inactive_or_passwordless_user():
    from backend.services.auth_service import AuthService

    db = AsyncMock()
    svc = AuthService(db, get_settings())
    user = MagicMock(is_active=False, hashed_password="x")
    svc.users.get_by_email = AsyncMock(return_value=user)
    assert await svc.create_password_reset("a@b.com") is None

    user.is_active = True
    user.hashed_password = None
    assert await svc.create_password_reset("a@b.com") is None


@pytest.mark.asyncio
async def test_create_password_reset_returns_token_for_active_user():
    from backend.services.auth_service import AuthService

    db = AsyncMock()
    svc = AuthService(db, get_settings())
    user = MagicMock(id="u1", is_active=True, hashed_password="hashed")
    svc.users.get_by_email = AsyncMock(return_value=user)
    svc.reset_tokens.invalidate_for_user = AsyncMock()
    svc.reset_tokens.create = AsyncMock()

    with patch(
        "backend.services.auth_service.secrets.token_urlsafe",
        return_value="raw-token-value",
    ):
        result = await svc.create_password_reset("user@example.com")

    assert result is not None
    raw, returned_user = result
    assert raw == "raw-token-value"
    assert returned_user is user
    svc.reset_tokens.invalidate_for_user.assert_awaited_with("u1")
    svc.reset_tokens.create.assert_awaited_once()
