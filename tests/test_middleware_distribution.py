"""Distribution access middleware — publisher capability and rejection."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.db.models import UserTier
from backend.middleware.distribution import _install_has_publisher, require_distribution_access
from core.distribution.errors import DistributionProRequired


def _licenses_result(licenses: list) -> MagicMock:
    """Mock SQLAlchemy Result for ``select(InstallLicense)...scalars().all()``."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = licenses
    return result


@pytest.mark.asyncio
async def test_pro_user_passes():
    user = SimpleNamespace(id="u1", tier=UserTier.PRO)
    db = AsyncMock()
    db.get = AsyncMock(return_value=user)
    assert await require_distribution_access("u1", db) == "u1"


@pytest.mark.asyncio
async def test_install_license_passes_free_user():
    user = SimpleNamespace(id="u1", tier=UserTier.FREE)
    lic = SimpleNamespace(
        tier=UserTier.PRO,
        status="activated",
        capabilities=["studio", "publisher"],
        order_id=None,
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=user)
    db.execute = AsyncMock(return_value=_licenses_result([lic]))
    assert await require_distribution_access("u1", db) == "u1"


@pytest.mark.asyncio
async def test_free_user_without_license_rejected():
    user = SimpleNamespace(id="u1", tier=UserTier.FREE)
    db = AsyncMock()
    db.get = AsyncMock(return_value=user)
    db.execute = AsyncMock(return_value=_licenses_result([]))
    with pytest.raises(DistributionProRequired):
        await require_distribution_access("u1", db)


@pytest.mark.asyncio
async def test_install_has_publisher_true():
    lic = SimpleNamespace(
        tier=UserTier.PRO,
        status="activated",
        capabilities=None,
        order_id=None,
    )
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_licenses_result([lic]))
    assert await _install_has_publisher(db) is True


@pytest.mark.asyncio
async def test_install_has_publisher_false_without_caps():
    lic = SimpleNamespace(
        tier=UserTier.FREE,
        status="activated",
        capabilities=[],
        order_id=None,
    )
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_licenses_result([lic]))
    assert await _install_has_publisher(db) is False
