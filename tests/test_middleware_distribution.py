"""Distribution access middleware — Pro user, install license, and rejection."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.db.models import UserTier
from backend.middleware.distribution import _install_has_pro_license, require_distribution_access
from core.distribution.errors import DistributionProRequired


@pytest.mark.asyncio
async def test_pro_user_passes():
    user = SimpleNamespace(id="u1", tier=UserTier.PRO)
    db = AsyncMock()
    db.get = AsyncMock(return_value=user)
    assert await require_distribution_access("u1", db) == "u1"


@pytest.mark.asyncio
async def test_install_license_passes_free_user():
    user = SimpleNamespace(id="u1", tier=UserTier.FREE)
    db = AsyncMock()
    db.get = AsyncMock(return_value=user)
    result = MagicMock()
    result.scalar_one_or_none.return_value = "lic-1"
    db.execute = AsyncMock(return_value=result)
    assert await require_distribution_access("u1", db) == "u1"


@pytest.mark.asyncio
async def test_free_user_without_license_rejected():
    user = SimpleNamespace(id="u1", tier=UserTier.FREE)
    db = AsyncMock()
    db.get = AsyncMock(return_value=user)
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    with pytest.raises(DistributionProRequired):
        await require_distribution_access("u1", db)


@pytest.mark.asyncio
async def test_install_has_pro_license_true():
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = "lic"
    db.execute = AsyncMock(return_value=result)
    assert await _install_has_pro_license(db) is True
