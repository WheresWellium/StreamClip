"""License status endpoint with persisted entitlement."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.db.models import UserTier
from core.config import get_settings
from core.licensing import activate_license_key


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
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/license/status", params={"machine_id": "machine-abc"})

    cfg.licensing.license_file = old_file
    assert resp.status_code == 200
    body = resp.json()
    assert body["active"] is True
    assert body["tier"] == "pro"


@pytest.mark.asyncio
async def test_license_status_invalid_token(tmp_path, monkeypatch):
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
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/license/status", params={"machine_id": "machine-abc"})

    cfg.licensing.license_file = old_file
    assert resp.status_code == 200
    assert resp.json()["active"] is False
