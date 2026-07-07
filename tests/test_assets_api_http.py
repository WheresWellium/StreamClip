"""Assets API HTTP coverage."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import backend.api.assets as assets_api
from backend.db.session import get_db
from backend.middleware.auth import get_current_user_id, require_user_id


@pytest.fixture
def assets_client(app, client, monkeypatch):
    session = MagicMock()
    session.commit = AsyncMock()

    async def fake_db():
        yield session

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[require_user_id] = lambda: "user-1"
    app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    yield client, session
    for dep in (get_db, require_user_id, get_current_user_id):
        app.dependency_overrides.pop(dep, None)


@pytest.mark.asyncio
async def test_list_assets(assets_client, monkeypatch):
    client, _ = assets_client
    asset = SimpleNamespace(
        id="a1", name="logo", asset_type="png", storage_key="k",
        sfx_storage_key=None, description="d", tags=[], default_duration_secs=1.0,
        owner_id="user-1", is_public=False, use_count=0,
    )

    class FakeRepo:
        def __init__(self, db):
            pass

        async def list_for_user(self, user_id):
            return [asset]

    monkeypatch.setattr(assets_api, "AssetRepository", FakeRepo)
    resp = await client.get("/api/assets")
    assert resp.status_code == 200
    assert resp.json()[0]["id"] == "a1"


@pytest.mark.asyncio
async def test_create_asset_limit(assets_client, monkeypatch):
    client, _ = assets_client

    class FakeRepo:
        def __init__(self, db):
            pass

        async def list_for_user(self, user_id):
            return [SimpleNamespace(owner_id="user-1")] * 50

        async def create(self, **fields):
            raise AssertionError("should not create")

    monkeypatch.setattr(assets_api, "AssetRepository", FakeRepo)
    resp = await client.post(
        "/api/assets",
        json={
            "name": "x",
            "asset_type": "png",
            "storage_key": "assets/x.png",
            "description": "logo asset",
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_asset_success(assets_client, monkeypatch):
    client, session = assets_client
    created = SimpleNamespace(
        id="a2", name="logo", asset_type="png", storage_key="k",
        sfx_storage_key=None, description="logo asset", tags=[], default_duration_secs=2.5,
        owner_id="user-1", is_public=False, use_count=0,
    )

    class FakeRepo:
        def __init__(self, db):
            pass

        async def list_for_user(self, user_id):
            return []

        async def create(self, **fields):
            return created

    monkeypatch.setattr(assets_api, "AssetRepository", FakeRepo)
    resp = await client.post(
        "/api/assets",
        json={
            "name": "logo",
            "asset_type": "png",
            "storage_key": "assets/logo.png",
            "description": "logo asset",
        },
    )
    assert resp.status_code == 201
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_delete_asset_not_found(assets_client, monkeypatch):
    client, session = assets_client

    class FakeRepo:
        def __init__(self, db):
            pass

        async def get(self, asset_id):
            return None

        async def delete(self, asset_id):
            pass

    monkeypatch.setattr(assets_api, "AssetRepository", FakeRepo)
    resp = await client.delete("/api/assets/missing")
    assert resp.status_code == 404
