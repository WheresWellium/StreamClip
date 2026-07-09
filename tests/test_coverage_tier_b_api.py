"""Tier B API/service ratchet — error paths and validation branches toward 100% line."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.api.schemas import RegisterRequest
from backend.db.session import get_db
from backend.middleware.auth import AuthError
from core.config import get_settings


@pytest.mark.asyncio
async def test_register_links_licenses_by_email(app, client, monkeypatch):
    user = SimpleNamespace(
        id="u1",
        email="a@b.com",
        display_name="A",
        tier="free",
        is_active=True,
        jobs_used_this_month=0,
        minutes_processed_this_month=0.0,
    )

    class FakeAuthService:
        def __init__(self, db, cfg) -> None:
            pass

        async def register(self, email, password, *, display_name=None):
            return user

    monkeypatch.setattr("backend.api.auth.AuthService", FakeAuthService)
    link = AsyncMock()
    monkeypatch.setattr("backend.api.auth.link_licenses_by_email", link)

    async def fake_db():
        session = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = fake_db
    try:
        resp = await client.post(
            "/api/auth/register",
            json={"email": "a@b.com", "password": "password123", "display_name": "A"},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 201
    link.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_invalid_token(client, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr("backend.api.auth.get_settings", lambda: cfg)
    monkeypatch.setattr(
        "backend.api.auth.decode_token",
        MagicMock(side_effect=AuthError("bad token")),
    )
    resp = await client.post("/api/auth/refresh", json={"refresh_token": "invalid"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_distribution_publish_requires_auth(client):
    resp = await client.post(
        "/api/distribution/publish",
        json={"clip_id": "c1", "platform": "youtube_shorts", "title": "T"},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_distribution_schedule_requires_auth(client):
    resp = await client.post(
        "/api/distribution/schedule",
        json={
            "clip_id": "c1",
            "platform": "youtube_shorts",
            "scheduled_at": "2030-01-01T12:00:00Z",
            "title": "T",
        },
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_jobs_cancel_not_found(client):
    resp = await client.post(
        "/api/jobs/missing-job/cancel",
        headers={"X-Device-Id": "tierb-device01"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_local_storage_unavailable_in_docker(client):
    resp = await client.get("/storage/uploads/test.mp4")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_support_bug_report_empty_categories(client):
    resp = await client.post(
        "/api/support/bug-reports",
        json={"categories": [], "severity": "low", "description": "x"},
        headers={"X-Device-Id": "tierb-device01"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_license_status_missing_machine_id(client):
    resp = await client.get("/api/license/status")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_license_status_with_machine_id(client):
    resp = await client.get("/api/license/status", params={"machine_id": "test-machine-001"})
    assert resp.status_code == 200
    body = resp.json()
    assert "active" in body


@pytest.mark.asyncio
async def test_main_lifespan_inprocess_worker(monkeypatch):
    from backend.main import lifespan

    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")
    app = MagicMock()
    engine = MagicMock()
    engine.dispose = AsyncMock()
    conn = AsyncMock()
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=None)
    engine.connect.return_value = conn

    with patch("backend.main.get_settings", return_value=cfg):
        with patch("backend.main._init_sentry"):
            with patch("backend.main.init_opentelemetry"):
                with patch("backend.db.session.get_engine", return_value=engine):
                    with patch("core.inprocess_worker.start_inprocess_worker") as start:
                        with patch("core.inprocess_worker.stop_inprocess_worker") as stop:
                            async with lifespan(app):
                                pass
                            start.assert_called_once()
                            stop.assert_called_once()


@pytest.mark.asyncio
async def test_forgot_password_dispatches_reset_email(app, client, monkeypatch):
    user = SimpleNamespace(email="reset@test.local")

    class FakeAuthService:
        def __init__(self, db, cfg) -> None:
            pass

        async def create_password_reset(self, email: str):
            return ("raw-reset-token", user)

    monkeypatch.setattr("backend.api.auth.AuthService", FakeAuthService)

    async def fake_db():
        session = AsyncMock()
        session.commit = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = fake_db
    cfg = get_settings(reload=True)
    cfg.distribution.web_origin = "http://localhost:3000"
    try:
        with patch("backend.api.auth.get_settings", return_value=cfg):
            with patch("backend.api.auth.dispatch_task") as dispatch:
                resp = await client.post(
                    "/api/auth/forgot-password",
                    json={"email": user.email},
                )
        assert resp.status_code == 200
        dispatch.assert_called_once()
        args = dispatch.call_args.kwargs["args"]
        assert args[0] == user.email
        assert "raw-reset-token" in args[1]
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_reset_password_endpoint_commits(app, client, monkeypatch):
    class FakeAuthService:
        def __init__(self, db, cfg) -> None:
            pass

        async def reset_password(self, token: str, new_password: str):
            return SimpleNamespace(email="reset@test.local")

    monkeypatch.setattr("backend.api.auth.AuthService", FakeAuthService)

    async def fake_db():
        session = AsyncMock()
        session.commit = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = fake_db
    try:
        resp = await client.post(
            "/api/auth/reset-password",
            json={
                "token": "valid-reset-token-value",
                "new_password": "newpassword123",
            },
        )
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.pop(get_db, None)
