"""Rapid consecutive support posts must not 500 on SQLite."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient

from backend.db.session import dispose_engine, get_sync_engine_url
from backend.main import create_app
from core.config import get_settings


@pytest.fixture
async def sqlite_support_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "support.db"
    db_posix = db_path.resolve().as_posix()
    monkeypatch.setenv("STREAMCLIP_DATABASE__URL", f"sqlite+aiosqlite:///{db_posix}")
    monkeypatch.setenv("STREAMCLIP_DATABASE__SYNC_URL", f"sqlite:///{db_posix}")
    monkeypatch.setenv("STREAMCLIP_RATE_LIMIT__ENABLED", "false")
    get_settings(reload=True)
    await dispose_engine()

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", get_sync_engine_url())
    command.upgrade(alembic_cfg, "head")

    app = create_app()
    transport = ASGITransport(app=app)
    headers = {"X-Device-Id": "smoke0123456789abcdef0123456789ab"}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as ac:
        yield ac
    await dispose_engine()
    get_settings(reload=True)


@pytest.mark.asyncio
async def test_two_rapid_bug_reports_succeed(sqlite_support_client):
    with patch("backend.api.support.ops_webhook_status", return_value="queued"), patch(
        "backend.api.support.bug_report_email_status",
        return_value="skipped_unconfigured",
    ), patch("backend.api.support.dispatch_task"):
        r1 = await sqlite_support_client.post(
            "/api/support/bug-reports",
            json={
                "categories": ["ui"],
                "severity": "medium",
                "message": "first rapid report",
                "environment": {"os": "test"},
            },
        )
        r2 = await sqlite_support_client.post(
            "/api/support/bug-reports",
            json={
                "categories": ["ui"],
                "severity": "low",
                "message": "second rapid report",
                "environment": {"os": "test"},
            },
        )
    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text
    assert r1.json()["ops_notification"] == "queued"
    assert r2.json()["ops_notification"] == "queued"
    assert r1.json()["id"] != r2.json()["id"]


@pytest.mark.asyncio
async def test_two_rapid_beta_feedback_succeed(sqlite_support_client):
    with patch("backend.api.support.ops_webhook_status", return_value="queued"), patch(
        "backend.api.support.bug_report_email_status",
        return_value="skipped_unconfigured",
    ), patch("backend.api.support.dispatch_task"):
        r1 = await sqlite_support_client.post(
            "/api/support/beta-feedback",
            json={"topic": "other", "message": "feedback one"},
        )
        r2 = await sqlite_support_client.post(
            "/api/support/beta-feedback",
            json={"topic": "idea", "message": "feedback two"},
        )
    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text
