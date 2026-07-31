"""AuthService unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.services.auth_service import AuthService
from core.config import get_settings
from core.errors import AuthError, EmailAlreadyRegisteredError


@pytest.mark.asyncio
async def test_register_validation():
    db = AsyncMock()
    svc = AuthService(db, get_settings())
    with pytest.raises(AuthError):
        await svc.register("bad", "short")
    with pytest.raises(AuthError, match="letters and at least one number"):
        await svc.register("a@b.com", "longenough")
    with pytest.raises(AuthError, match="too common"):
        await svc.register("a@b.com", "password1")


@pytest.mark.asyncio
async def test_register_duplicate():
    db = AsyncMock()
    svc = AuthService(db, get_settings())
    svc.users.get_by_email = AsyncMock(return_value=MagicMock())
    with pytest.raises(EmailAlreadyRegisteredError) as exc_info:
        await svc.register("a@b.com", "password12")
    assert exc_info.value.http_status == 409


@pytest.mark.asyncio
async def test_authenticate_paths():
    db = AsyncMock()
    svc = AuthService(db, get_settings())
    svc.users.get_by_email = AsyncMock(return_value=None)
    with pytest.raises(AuthError):
        await svc.authenticate("a@b.com", "password12")

    user = MagicMock(hashed_password=None, is_active=True)
    svc.users.get_by_email = AsyncMock(return_value=user)
    with pytest.raises(AuthError):
        await svc.authenticate("a@b.com", "password12")

    from backend.middleware.auth import hash_password

    user.hashed_password = hash_password("password12")
    svc.users.get_by_email = AsyncMock(return_value=user)
    out = await svc.authenticate("a@b.com", "password12")
    assert out is user

    user.is_active = False
    with pytest.raises(AuthError):
        await svc.authenticate("a@b.com", "password12")


@pytest.mark.asyncio
async def test_get_active_user():
    db = AsyncMock()
    svc = AuthService(db, get_settings())
    svc.users.get = AsyncMock(return_value=None)
    with pytest.raises(AuthError):
        await svc.get_active_user("id")


@pytest.mark.asyncio
async def test_update_profile_validation():
    db = AsyncMock()
    svc = AuthService(db, get_settings())
    user = MagicMock(id="u1", is_active=True, display_name="Old")
    svc.users.get = AsyncMock(return_value=user)
    svc.users.update_display_name = AsyncMock()

    with pytest.raises(AuthError):
        await svc.update_profile("u1", display_name="   ")
    with pytest.raises(AuthError):
        await svc.update_profile("u1", display_name="x" * 121)

    out = await svc.update_profile("u1", display_name="New Name")
    assert out.display_name == "New Name"
    svc.users.update_display_name.assert_awaited_with("u1", "New Name")


@pytest.mark.asyncio
async def test_change_password_paths():
    from backend.middleware.auth import hash_password

    db = AsyncMock()
    svc = AuthService(db, get_settings())
    user = MagicMock(
        id="u1",
        is_active=True,
        hashed_password=hash_password("password12"),
    )
    svc.users.get = AsyncMock(return_value=user)
    svc.users.update_password = AsyncMock()

    with pytest.raises(AuthError):
        await svc.change_password("u1", "wrong", "newpassword1")
    with pytest.raises(AuthError):
        await svc.change_password("u1", "password12", "short")
    with pytest.raises(AuthError):
        await svc.change_password("u1", "password12", "password12")

    await svc.change_password("u1", "password12", "newpassword1")
    svc.users.update_password.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_password_reset_unknown_user():
    db = AsyncMock()
    svc = AuthService(db, get_settings())
    svc.users.get_by_email = AsyncMock(return_value=None)
    assert await svc.create_password_reset("nobody@example.com") is None


@pytest.mark.asyncio
async def test_reset_password_invalid_token():
    db = AsyncMock()
    svc = AuthService(db, get_settings())
    svc.reset_tokens.get_valid_by_hash = AsyncMock(return_value=None)
    with pytest.raises(AuthError):
        await svc.reset_password("bad-token", "password1234")

