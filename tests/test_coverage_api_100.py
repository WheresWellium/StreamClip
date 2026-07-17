"""Line-coverage sweep for backend/api handlers (MASTER_TODO section 3.10).

Async endpoint bodies are exercised with mocked dependencies: coverage
attribution is unreliable for handler lines that follow a real (event-loop
suspending) DB await, so the project's coverage suite mocks the session and
service seams — matching test_coverage_tier_b_api.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import backend.api.assets as assets_api
import backend.api.auth as auth_api
import backend.api.settings as settings_api
import backend.api.support as support_api
import backend.api.templates as templates_api
import backend.api.vault as vault_api
from backend.db.session import get_db
from backend.middleware.auth import create_refresh_token, get_current_user_id, require_user_id
from core.config import get_settings


def _fake_user(uid: str = "u1"):
    return SimpleNamespace(
        id=uid,
        email="a@b.com",
        display_name="A",
        tier="free",
        is_active=True,
        jobs_used_this_month=0,
        minutes_processed_this_month=0.0,
    )


def _override_db(app):
    async def fake_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = fake_db


def _clear(app, *deps):
    for dep in deps:
        app.dependency_overrides.pop(dep, None)


# ─── auth.py: login / refresh / me / update_me / change_password ──────────────

@pytest.mark.asyncio
async def test_login_success(app, client, monkeypatch):
    user = _fake_user()

    class FakeSvc:
        def __init__(self, db, cfg):
            pass

        async def authenticate(self, email, password):
            return user

    monkeypatch.setattr(auth_api, "AuthService", FakeSvc)
    _override_db(app)
    try:
        resp = await client.post("/api/auth/login", json={"email": "a@b.com", "password": "x"})
        assert resp.status_code == 200
        assert resp.json()["access_token"]
    finally:
        _clear(app, get_db)


@pytest.mark.asyncio
async def test_refresh_success(app, client, monkeypatch):
    user = _fake_user()

    class FakeSvc:
        def __init__(self, db, cfg):
            pass

        async def get_active_user(self, user_id):
            return user

    monkeypatch.setattr(auth_api, "AuthService", FakeSvc)
    _override_db(app)
    token = create_refresh_token("u1", get_settings())
    try:
        resp = await client.post("/api/auth/refresh", json={"refresh_token": token})
        assert resp.status_code == 200
        assert resp.json()["access_token"]
    finally:
        _clear(app, get_db)


@pytest.mark.asyncio
async def test_me_and_update_and_change_password(app, client, monkeypatch):
    user = _fake_user()

    class FakeSvc:
        def __init__(self, db, cfg):
            pass

        async def get_active_user(self, user_id):
            return user

        async def update_profile(self, user_id, *, display_name):
            user.display_name = display_name
            return user

        async def change_password(self, user_id, current, new):
            return None

    monkeypatch.setattr(auth_api, "AuthService", FakeSvc)
    _override_db(app)
    app.dependency_overrides[require_user_id] = lambda: "u1"
    try:
        me = await client.get("/api/auth/me")
        assert me.status_code == 200

        upd = await client.patch("/api/auth/me", json={"display_name": "New"})
        assert upd.status_code == 200
        assert upd.json()["display_name"] == "New"

        chg = await client.post(
            "/api/auth/change-password",
            json={"current_password": "oldpw123", "new_password": "newpw1234"},
        )
        assert chg.status_code == 200
    finally:
        _clear(app, get_db, require_user_id)


# ─── settings.py: webhook / privacy / feedback ───────────────────────────────

@pytest.mark.asyncio
async def test_webhook_get_and_update(app, client, monkeypatch):
    repo = MagicMock()
    repo.get = AsyncMock(return_value=SimpleNamespace(webhook_url="https://h", data_contribution_opt_in=True))
    repo.update_webhook = AsyncMock()
    monkeypatch.setattr(settings_api, "UserRepository", lambda db: repo)
    _override_db(app)
    app.dependency_overrides[require_user_id] = lambda: "u1"
    try:
        got = await client.get("/api/settings/webhook")
        assert got.status_code == 200 and got.json()["configured"] is True

        put = await client.put(
            "/api/settings/webhook",
            json={"webhook_url": "https://h", "webhook_secret": "s"},
        )
        assert put.status_code == 200
    finally:
        _clear(app, get_db, require_user_id)


@pytest.mark.asyncio
async def test_privacy_get_and_update(app, client, monkeypatch):
    repo = MagicMock()
    repo.get = AsyncMock(return_value=SimpleNamespace(webhook_url=None, data_contribution_opt_in=True))
    repo.set_data_contribution_opt_in = AsyncMock()
    monkeypatch.setattr(settings_api, "UserRepository", lambda db: repo)
    _override_db(app)
    app.dependency_overrides[require_user_id] = lambda: "u1"
    try:
        got = await client.get("/api/settings/privacy")
        assert got.status_code == 200

        put = await client.put("/api/settings/privacy", json={"data_contribution_opt_in": True})
        assert put.status_code == 200 and put.json()["data_contribution_opt_in"] is True
    finally:
        _clear(app, get_db, require_user_id)


@pytest.mark.asyncio
async def test_clip_feedback_clip_missing(app, client, monkeypatch):
    clips = MagicMock()
    clips.get = AsyncMock(return_value=None)
    monkeypatch.setattr(settings_api, "ClipRepository", lambda db: clips)
    _override_db(app)
    try:
        resp = await client.post(
            "/api/settings/clips/nope/feedback",
            json={"rating": 5},
        )
        assert resp.status_code == 404
    finally:
        _clear(app, get_db)


@pytest.mark.asyncio
async def test_settings_user_not_found_branches(app, client, monkeypatch):
    repo = MagicMock()
    repo.get = AsyncMock(return_value=None)
    monkeypatch.setattr(settings_api, "UserRepository", lambda db: repo)
    _override_db(app)
    app.dependency_overrides[require_user_id] = lambda: "ghost"
    try:
        assert (await client.get("/api/settings/webhook")).status_code >= 400
        assert (await client.get("/api/settings/privacy")).status_code >= 400
    finally:
        _clear(app, get_db, require_user_id)


# ─── support.py: bug report + beta feedback ───────────────────────────────────

@pytest.mark.asyncio
async def test_bug_report_and_beta_feedback(app, client, monkeypatch):
    report = SimpleNamespace(
        id="r1",
        status="open",
        severity="low",
        categories=["ui"],
        created_at=datetime.now(timezone.utc),
    )
    bug_repo = MagicMock()
    bug_repo.create = AsyncMock(return_value=report)
    job_repo = MagicMock()
    job_repo.get = AsyncMock(return_value=None)  # unknown job -> job_id reset (82)
    monkeypatch.setattr(support_api, "BugReportRepository", lambda db: bug_repo)
    monkeypatch.setattr(support_api, "JobRepository", lambda db: job_repo)
    _override_db(app)
    try:
        bug = await client.post(
            "/api/support/bug-reports",
            json={
                "message": "Editor is broken somehow",
                "categories": ["ui"],
                "severity": "low",
                "job_id": "ghost-job",
            },
        )
        assert bug.status_code == 201, bug.text

        fb = await client.post(
            "/api/support/beta-feedback",
            json={"topic": "idea", "message": "Add a dark mode toggle please"},
        )
        assert fb.status_code == 201, fb.text
        assert fb.json()["topic"] == "idea"
    finally:
        _clear(app, get_db)


# ─── templates.py: create limit + delete not-found ────────────────────────────

@pytest.mark.asyncio
async def test_template_create_delete_and_limit(app, client, monkeypatch):
    repo = MagicMock()
    repo.list_for_user = AsyncMock(return_value=[])
    repo.create = AsyncMock(return_value=SimpleNamespace(
        id="t1", name="My", config_json={}, created_at=datetime.now(timezone.utc),
    ))
    repo.delete = AsyncMock(return_value=False)
    monkeypatch.setattr(templates_api, "JobTemplateRepository", lambda db: repo)
    _override_db(app)
    app.dependency_overrides[require_user_id] = lambda: "u1"
    try:
        created = await client.post("/api/templates", json={"name": "My", "config_json": {}})
        assert created.status_code in (200, 201), created.text

        missing = await client.delete("/api/templates/t1")
        assert missing.status_code >= 400  # delete returns False -> not found (70)

        repo.list_for_user = AsyncMock(return_value=list(range(20)))
        overflow = await client.post("/api/templates", json={"name": "X", "config_json": {}})
        assert overflow.status_code >= 400  # limit reached (48-51)
    finally:
        _clear(app, get_db, require_user_id)


# ─── assets.py: delete success + not found ────────────────────────────────────

@pytest.mark.asyncio
async def test_asset_delete_success_and_notfound(app, client, monkeypatch):
    asset = SimpleNamespace(owner_id="owner-1")
    repo = MagicMock()
    repo.get = AsyncMock(return_value=asset)
    repo.delete = AsyncMock()
    monkeypatch.setattr(assets_api, "AssetRepository", lambda db: repo)
    _override_db(app)
    app.dependency_overrides[require_user_id] = lambda: "owner-1"
    try:
        ok = await client.delete("/api/assets/asset-1")
        assert ok.status_code == 204
        repo.delete.assert_awaited_with("asset-1")

        repo.get = AsyncMock(return_value=None)
        assert (await client.delete("/api/assets/asset-2")).status_code >= 400
    finally:
        _clear(app, get_db, require_user_id)


# ─── vault.py: delete cleanup swallows storage errors + not found ─────────────

@pytest.mark.asyncio
async def test_vault_delete_swallows_storage_errors(app, client, monkeypatch):
    row = SimpleNamespace(storage_key="clips/a.mp4", thumb_storage_key="clips/a.jpg")
    repo = MagicMock()
    repo.get_for_user = AsyncMock(return_value=row)
    repo.delete = AsyncMock()
    storage = MagicMock()
    storage.delete.side_effect = RuntimeError("boom")
    monkeypatch.setattr(vault_api, "VaultClipRepository", lambda db: repo)
    monkeypatch.setattr(vault_api, "make_storage", lambda cfg: storage)
    _override_db(app)
    app.dependency_overrides[require_user_id] = lambda: "owner-1"
    try:
        resp = await client.delete("/api/vault/clips/vc-1")
        assert resp.status_code == 204
        assert storage.delete.call_count == 2
        repo.delete.assert_awaited_with("vc-1")
    finally:
        _clear(app, get_db, require_user_id)


@pytest.mark.asyncio
async def test_vault_delete_not_found(app, client, monkeypatch):
    repo = MagicMock()
    repo.get_for_user = AsyncMock(return_value=None)
    monkeypatch.setattr(vault_api, "VaultClipRepository", lambda db: repo)
    monkeypatch.setattr(vault_api, "make_storage", lambda cfg: MagicMock())
    _override_db(app)
    app.dependency_overrides[require_user_id] = lambda: "owner-1"
    try:
        assert (await client.delete("/api/vault/clips/missing")).status_code == 404
    finally:
        _clear(app, get_db, require_user_id)
