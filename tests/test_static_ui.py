"""Tests for static UI mount (ADR-001 §4.7)."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import create_app
from core.config import get_settings


@pytest.fixture
def static_ui_env(tmp_path, monkeypatch):
    ui = tmp_path / "ui"
    ui.mkdir()
    (ui / "index.html").write_text("<html><body>StreamClip UI</body></html>", encoding="utf-8")
    (ui / "_next").mkdir()
    (ui / "_next" / "chunk.js").write_text("//", encoding="utf-8")
    (ui / "jobs").mkdir()
    (ui / "jobs" / "index.html").write_text("<html><body>Jobs</body></html>", encoding="utf-8")

    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.web, "serve_static", True)
    monkeypatch.setattr(cfg.web, "static_dir", ui)
    return ui


@pytest.mark.asyncio
async def test_static_ui_serves_index(static_ui_env):
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "StreamClip UI" in resp.text


@pytest.mark.asyncio
async def test_static_ui_serves_nested_route(static_ui_env):
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/jobs/")
        assert resp.status_code == 200
        assert "Jobs" in resp.text


@pytest.mark.asyncio
async def test_static_ui_does_not_shadow_api(static_ui_env):
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_static_ui_disabled_by_default(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.web, "serve_static", False)
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
        assert resp.status_code == 404
