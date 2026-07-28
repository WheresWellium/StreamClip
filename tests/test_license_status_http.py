"""License status endpoint with persisted entitlement."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.db.models import UserTier
from backend.db.session import get_db
from core.config import get_settings
from core.licensing import activate_license_key
import backend.api.license as license_api


@pytest.mark.asyncio
async def test_license_status_active(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    old_file = cfg.licensing.license_file
    cfg.licensing.license_file = tmp_path / "lic.json"
    cfg.licensing.enabled = True

    token, _ = activate_license_key(
        "SCPRO-TEST-TEST-TEST-TEST",
        "machine-abc",
        tier=UserTier.PRO,
        cfg=cfg,
    )
    cfg.licensing.license_file.write_text(
        json.dumps({"entitlement_jwt": token}),
        encoding="utf-8",
    )

    from backend.main import create_app
    from httpx import ASGITransport, AsyncClient

    app = create_app()
    repo = MagicMock()
    repo.get_by_key_hash = AsyncMock(return_value=None)
    monkeypatch.setattr(license_api, "InstallLicenseRepository", lambda db: repo)

    async def fake_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = fake_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/license/status", params={"machine_id": "machine-abc"})
    finally:
        app.dependency_overrides.pop(get_db, None)
        cfg.licensing.license_file = old_file

    assert resp.status_code == 200
    body = resp.json()
    assert body["active"] is True
    assert body["tier"] == "pro"


@pytest.mark.asyncio
async def test_license_status_invalid_token(tmp_path, monkeypatch):
    """Malformed JWT falls through to record renew; empty DB => inactive."""
    cfg = get_settings(reload=True)
    old_file = cfg.licensing.license_file
    cfg.licensing.license_file = tmp_path / "lic.json"
    cfg.licensing.license_file.write_text(
        json.dumps({"entitlement_jwt": "not-valid"}),
        encoding="utf-8",
    )

    from backend.main import create_app
    from httpx import ASGITransport, AsyncClient

    app = create_app()
    # Avoid real asyncpg: invalid tokens call _renew_from_records(db.execute...).
    db = AsyncMock()
    result = SimpleNamespace(scalar_one_or_none=lambda: None)
    db.execute = AsyncMock(return_value=result)

    async def fake_db():
        yield db

    app.dependency_overrides[get_db] = fake_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/license/status", params={"machine_id": "machine-abc"})
    finally:
        app.dependency_overrides.pop(get_db, None)
        cfg.licensing.license_file = old_file

    assert resp.status_code == 200
    assert resp.json()["active"] is False
