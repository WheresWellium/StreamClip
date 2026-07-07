"""Device onboarding API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

import backend.api.devices as devices_api
from backend.db.session import get_db
from backend.middleware.auth import get_device_id


@pytest.fixture
def devices_client(app, client, monkeypatch):
    session = MagicMock()
    session.commit = AsyncMock()

    async def fake_db():
        yield session

    repo = MagicMock()
    repo.mark_onboarding_complete = AsyncMock()

    monkeypatch.setattr(devices_api, "DeviceRepository", lambda db: repo)
    app.dependency_overrides[get_db] = fake_db
    yield client, repo, session
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_onboarding_complete_from_body(devices_client):
    client, repo, session = devices_client
    resp = await client.post(
        "/api/devices/onboarding-complete",
        json={"device_id": "device-abc12345"},
    )
    assert resp.status_code == 200
    assert resp.json()["device_id"] == "device-abc12345"
    repo.mark_onboarding_complete.assert_awaited_with("device-abc12345")
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_onboarding_complete_prefers_header_when_body_empty(devices_client, app):
    client, repo, session = devices_client
    app.dependency_overrides[get_device_id] = lambda: "header-device1"
    resp = await client.post(
        "/api/devices/onboarding-complete",
        json={"device_id": ""},
    )
    app.dependency_overrides.pop(get_device_id, None)
    assert resp.status_code == 200
    repo.mark_onboarding_complete.assert_awaited_with("header-device1")


@pytest.mark.asyncio
async def test_onboarding_requires_device_id(devices_client, app):
    client, _, _ = devices_client
    app.dependency_overrides[get_device_id] = lambda: None
    resp = await client.post(
        "/api/devices/onboarding-complete",
        json={"device_id": ""},
    )
    app.dependency_overrides.pop(get_device_id, None)
    assert resp.status_code == 400
