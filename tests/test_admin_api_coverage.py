"""Focused coverage for backend/api/admin.py — require_admin dependency and
the license revoke endpoint's not-found / already-revoked / success paths.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from backend.api import admin as admin_mod
from backend.db.models import UserTier


@pytest.mark.asyncio
async def test_require_admin_rejects_missing_user():
    with patch.object(admin_mod, "UserRepository") as UR:
        UR.return_value.get = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc:
            await admin_mod.require_admin(user_id="u1", db=object())
        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_admin_rejects_non_admin_tier():
    user = SimpleNamespace(tier=UserTier.FREE, is_active=True)
    with patch.object(admin_mod, "UserRepository") as UR:
        UR.return_value.get = AsyncMock(return_value=user)
        with pytest.raises(HTTPException) as exc:
            await admin_mod.require_admin(user_id="u1", db=object())
        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_admin_rejects_inactive_admin():
    user = SimpleNamespace(tier=UserTier.ADMIN, is_active=False)
    with patch.object(admin_mod, "UserRepository") as UR:
        UR.return_value.get = AsyncMock(return_value=user)
        with pytest.raises(HTTPException) as exc:
            await admin_mod.require_admin(user_id="u1", db=object())
        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_admin_allows_active_admin():
    user = SimpleNamespace(tier=UserTier.ADMIN, is_active=True)
    with patch.object(admin_mod, "UserRepository") as UR:
        UR.return_value.get = AsyncMock(return_value=user)
        result = await admin_mod.require_admin(user_id="u1", db=object())
    assert result == "u1"


@pytest.mark.asyncio
async def test_revoke_license_not_found():
    with patch.object(admin_mod, "InstallLicenseRepository") as ILR:
        ILR.return_value.get = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc:
            await admin_mod.revoke_license("lic-missing", admin_id="admin1", db=object())
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_revoke_license_already_revoked_skips_revoke_call():
    lic = SimpleNamespace(status="revoked", license_key_hash="abcdef0123456789")
    db = SimpleNamespace(commit=AsyncMock())
    with patch.object(admin_mod, "InstallLicenseRepository") as ILR:
        repo = ILR.return_value
        repo.get = AsyncMock(return_value=lic)
        repo.revoke = AsyncMock()
        result = await admin_mod.revoke_license("lic-1", admin_id="admin1", db=db)
    repo.revoke.assert_not_called()
    db.commit.assert_not_called()
    assert result["license_id"] == "lic-1"
    assert result["status"] == "revoked"
    assert "note" in result  # JWT-invalidation known-limitation notice


@pytest.mark.asyncio
async def test_revoke_license_success_commits_and_logs():
    # user_id=None so the tier-downgrade path is skipped in this basic smoke test.
    lic = SimpleNamespace(status="issued", license_key_hash="abcdef0123456789", user_id=None)
    db = SimpleNamespace(commit=AsyncMock(), execute=AsyncMock())
    with patch.object(admin_mod, "InstallLicenseRepository") as ILR:
        repo = ILR.return_value
        repo.get = AsyncMock(return_value=lic)
        repo.revoke = AsyncMock()
        result = await admin_mod.revoke_license("lic-2", admin_id="admin1", db=db)
    repo.revoke.assert_called_once_with(lic)
    db.commit.assert_called_once()
    assert result["license_id"] == "lic-2"
    assert result["status"] == "revoked"
    assert "note" in result  # JWT-invalidation known-limitation notice


@pytest.mark.asyncio
async def test_revoke_license_downgrades_tier_when_no_other_active():
    lic = SimpleNamespace(
        status="issued",
        license_key_hash="abcdef0123456789",
        user_id="user-1",
        id="lic-3",
    )
    user = SimpleNamespace(tier=UserTier.PRO, id="user-1")
    db = SimpleNamespace(
        commit=AsyncMock(),
        execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None)),
    )
    with patch.object(admin_mod, "InstallLicenseRepository") as ILR, patch.object(
        admin_mod, "UserRepository"
    ) as UR:
        repo = ILR.return_value
        repo.get = AsyncMock(return_value=lic)
        repo.revoke = AsyncMock()
        UR.return_value.get = AsyncMock(return_value=user)
        result = await admin_mod.revoke_license("lic-3", admin_id="admin1", db=db)
    assert user.tier == UserTier.FREE
    db.commit.assert_called_once()
    assert result["status"] == "revoked"


@pytest.mark.asyncio
async def test_revoke_license_keeps_tier_when_other_active_license():
    lic = SimpleNamespace(
        status="issued",
        license_key_hash="abcdef0123456789",
        user_id="user-2",
        id="lic-4",
    )
    user = SimpleNamespace(tier=UserTier.PRO, id="user-2")
    db = SimpleNamespace(
        commit=AsyncMock(),
        execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: "other-lic")),
    )
    with patch.object(admin_mod, "InstallLicenseRepository") as ILR, patch.object(
        admin_mod, "UserRepository"
    ) as UR:
        repo = ILR.return_value
        repo.get = AsyncMock(return_value=lic)
        repo.revoke = AsyncMock()
        UR.return_value.get = AsyncMock(return_value=user)
        result = await admin_mod.revoke_license("lic-4", admin_id="admin1", db=db)
    assert user.tier == UserTier.PRO
    UR.return_value.get.assert_not_called()
    db.commit.assert_called_once()
    assert result["status"] == "revoked"


@pytest.mark.asyncio
async def test_list_bug_reports_returns_recent():
    from datetime import datetime, timezone

    report = SimpleNamespace(
        id="rpt-1",
        status="open",
        severity="high",
        categories=["ui"],
        message="Button stuck",
        user_id="u1",
        device_id="dev1",
        job_id=None,
        environment={"page": "/jobs"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    with patch.object(admin_mod, "BugReportRepository") as BR:
        BR.return_value.list_recent = AsyncMock(return_value=[report])
        result = await admin_mod.list_bug_reports(
            admin_id="admin1",
            db=object(),
            limit=50,
        )
    assert len(result) == 1
    assert result[0].id == "rpt-1"
    assert result[0].message == "Button stuck"
