"""AuthService unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.services.auth_service import AuthService
from core.config import get_settings
from core.errors import AuthError


@pytest.mark.asyncio
async def test_register_validation():
    db = AsyncMock()
    svc = AuthService(db, get_settings())
    with pytest.raises(AuthError):
        await svc.register("bad", "short")
    with pytest.raises(AuthError):
        await svc.register("a@b.com", "longenough")


@pytest.mark.asyncio
async def test_register_duplicate():
    db = AsyncMock()
    svc = AuthService(db, get_settings())
    svc.users.get_by_email = AsyncMock(return_value=MagicMock())
    with pytest.raises(AuthError):
        await svc.register("a@b.com", "password12")


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
