"""Line-coverage sweep for backend/api happy paths and error branches.

Targets remaining misses in auth, settings, support, templates, assets,
license, uploads and commerce so the server profile reaches 100% line
coverage (MASTER_TODO section 3.10 line pillar).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

import backend.api.settings as settings_api
import backend.api.vault as vault_api
from backend.db.session import get_db
from backend.middleware.auth import require_user_id


def _email() -> str:
    return f"cov-{uuid.uuid4().hex[:12]}@test.local"


async def _register(client, email: str | None = None, password: str = "password123"):
    email = email or _email()
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return email, password, {"Authorization": f"Bearer {token}"}


# ─── auth.py happy paths (login, refresh, me, update_me, change_password) ──────

@pytest.mark.asyncio
async def test_login_me_update_change_and_refresh(client):
    email, password, headers = await _register(client)

    # login (98-99)
    login = await client.post(
        "/api/auth/login",
        json={"email": email, "password": password, "remember_me": True},
    )
    assert login.status_code == 200, login.text
    refresh_token = login.json()["refresh_token"]

    # refresh success (121)
    refreshed = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["access_token"]

    # me (135)
    me = await client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == email

    # update_me (150-151)
    upd = await client.patch(
        "/api/auth/me",
        json={"display_name": "New Name"},
        headers=headers,
    )
    assert upd.status_code == 200
    assert upd.json()["display_name"] == "New Name"

    # change_password (166-167)
    chg = await client.post(
        "/api/auth/change-password",
        json={"current_password": password, "new_password": "brandnew123"},
        headers=headers,
    )
    assert chg.status_code == 200
    assert chg.json()["message"] == "Password updated"


# ─── settings.py webhook + privacy happy paths ────────────────────────────────

@pytest.mark.asyncio
async def test_webhook_and_privacy_roundtrip(client):
    _, _, headers = await _register(client)

    put = await client.put(
        "/api/settings/webhook",
        json={"webhook_url": "https://example.com/hook", "webhook_secret": "s3cr3t"},
        headers=headers,
    )
    assert put.status_code == 200
    assert put.json()["configured"] is True

    got = await client.get("/api/settings/webhook", headers=headers)
    assert got.status_code == 200
    assert got.json()["webhook_url"] == "https://example.com/hook"

    # update_privacy (106-107) + get_privacy happy path
    put_p = await client.put(
        "/api/settings/privacy",
        json={"data_contribution_opt_in": True},
        headers=headers,
    )
    assert put_p.status_code == 200
    assert put_p.json()["data_contribution_opt_in"] is True

    got_p = await client.get("/api/settings/privacy", headers=headers)
    assert got_p.status_code == 200


@pytest.mark.asyncio
async def test_settings_user_not_found_branches(app, client, monkeypatch):
    """get_webhook (46) and get_privacy (87-89) raise when the user row is gone."""
    repo = MagicMock()
    repo.get = AsyncMock(return_value=None)
    monkeypatch.setattr(settings_api, "UserRepository", lambda db: repo)
    app.dependency_overrides[require_user_id] = lambda: "ghost-user"
    try:
        wh = await client.get("/api/settings/webhook")
        assert wh.status_code >= 400
        pv = await client.get("/api/settings/privacy")
        assert pv.status_code >= 400
    finally:
        app.dependency_overrides.pop(require_user_id, None)


@pytest.mark.asyncio
async def test_clip_feedback_clip_not_found(client):
    """submit_clip_feedback raises 404 when the clip is missing (127-132)."""
    _, _, headers = await _register(client)
    resp = await client.post(
        "/api/settings/clips/does-not-exist/feedback",
        json={"rating": 5},
        headers=headers,
    )
    assert resp.status_code == 404


# ─── support.py bug report + beta feedback happy paths ────────────────────────

@pytest.mark.asyncio
async def test_bug_report_and_beta_feedback(client):
    _, _, headers = await _register(client)

    bug = await client.post(
        "/api/support/bug-reports",
        json={
            "message": "Something is broken in the editor",
            "categories": ["ui"],
            "severity": "low",
            "job_id": "nonexistent-job-id",
        },
        headers=headers,
    )
    assert bug.status_code == 201, bug.text
    assert "email_notification" in bug.json()

    fb = await client.post(
        "/api/support/beta-feedback",
        json={"topic": "idea", "message": "Please add dark mode toggle"},
        headers=headers,
    )
    assert fb.status_code == 201, fb.text
    assert fb.json()["topic"] == "idea"


# ─── templates.py limit + delete branches ─────────────────────────────────────

@pytest.mark.asyncio
async def test_template_create_delete_and_notfound(client):
    _, _, headers = await _register(client)

    created = await client.post(
        "/api/templates",
        json={"name": "My Template", "config_json": {"target_clips": 3}},
        headers=headers,
    )
    assert created.status_code in (200, 201), created.text
    tpl_id = created.json()["id"]

    deleted = await client.delete(f"/api/templates/{tpl_id}", headers=headers)
    assert deleted.status_code == 204

    # delete again -> not found (70)
    missing = await client.delete(f"/api/templates/{tpl_id}", headers=headers)
    assert missing.status_code >= 400


@pytest.mark.asyncio
async def test_template_limit_reached(app, client, monkeypatch):
    """create_template raises when 20 templates already exist (48-51)."""
    import backend.api.templates as templates_api

    repo = MagicMock()
    repo.list_for_user = AsyncMock(return_value=list(range(20)))
    monkeypatch.setattr(templates_api, "JobTemplateRepository", lambda db: repo)
    app.dependency_overrides[require_user_id] = lambda: "user-x"
    try:
        resp = await client.post(
            "/api/templates",
            json={"name": "Overflow", "config_json": {}},
        )
        assert resp.status_code >= 400
    finally:
        app.dependency_overrides.pop(require_user_id, None)


# ─── assets.py delete branches ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_asset_delete_success_and_notfound(app, client, monkeypatch):
    import backend.api.assets as assets_api

    asset = MagicMock()
    asset.owner_id = "owner-1"
    repo = MagicMock()
    repo.get = AsyncMock(return_value=asset)
    repo.delete = AsyncMock()
    session = MagicMock()
    session.commit = AsyncMock()

    async def fake_db():
        yield session

    monkeypatch.setattr(assets_api, "AssetRepository", lambda db: repo)
    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[require_user_id] = lambda: "owner-1"
    try:
        ok = await client.delete("/api/assets/asset-1")
        assert ok.status_code == 204
        repo.delete.assert_awaited_with("asset-1")

        # not found / wrong owner (81-82)
        repo.get = AsyncMock(return_value=None)
        missing = await client.delete("/api/assets/asset-2")
        assert missing.status_code >= 400
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(require_user_id, None)


# ─── vault.py delete with storage cleanup failures (168-179) ──────────────────

@pytest.mark.asyncio
async def test_vault_delete_swallows_storage_errors(app, client, monkeypatch):
    row = MagicMock()
    row.storage_key = "clips/a.mp4"
    row.thumb_storage_key = "clips/a.jpg"
    repo = MagicMock()
    repo.get_for_user = AsyncMock(return_value=row)
    repo.delete = AsyncMock()
    session = MagicMock()
    session.commit = AsyncMock()

    async def fake_db():
        yield session

    storage = MagicMock()
    storage.delete.side_effect = RuntimeError("boom")

    monkeypatch.setattr(vault_api, "VaultClipRepository", lambda db: repo)
    monkeypatch.setattr(vault_api, "make_storage", lambda cfg: storage)
    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[require_user_id] = lambda: "owner-1"
    try:
        resp = await client.delete("/api/vault/clips/vc-1")
        assert resp.status_code == 204
        assert storage.delete.call_count == 2
        repo.delete.assert_awaited_with("vc-1")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(require_user_id, None)


@pytest.mark.asyncio
async def test_vault_delete_not_found(app, client, monkeypatch):
    repo = MagicMock()
    repo.get_for_user = AsyncMock(return_value=None)
    session = MagicMock()
    session.commit = AsyncMock()

    async def fake_db():
        yield session

    monkeypatch.setattr(vault_api, "VaultClipRepository", lambda db: repo)
    monkeypatch.setattr(vault_api, "make_storage", lambda cfg: MagicMock())
    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[require_user_id] = lambda: "owner-1"
    try:
        resp = await client.delete("/api/vault/clips/missing")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(require_user_id, None)
