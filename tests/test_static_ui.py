"""Tests for static UI mount (ADR-001 §4.7)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import create_app
from backend.static_ui import resolve_static_dir
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
    # Next static export writes dynamic routes ([id]) to a literal "_" dir.
    (ui / "jobs" / "_").mkdir()
    (ui / "jobs" / "_" / "index.html").write_text(
        "<html><body>Job Detail</body></html>", encoding="utf-8"
    )
    (ui / "jobs" / "_" / "clips").mkdir()
    (ui / "jobs" / "_" / "clips" / "index.html").write_text(
        "<html><body>Job Clips</body></html>", encoding="utf-8"
    )

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
        assert "no-cache" in resp.headers.get("cache-control", "").lower()


@pytest.mark.asyncio
async def test_static_ui_spa_fallback_not_cached(static_ui_env):
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/jobs/")
        assert resp.status_code == 200
        assert "no-cache" in resp.headers.get("cache-control", "").lower()


@pytest.mark.asyncio
async def test_static_ui_serves_nested_route(static_ui_env):
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/jobs/")
        assert resp.status_code == 200
        assert "Jobs" in resp.text


@pytest.mark.asyncio
async def test_static_ui_serves_dynamic_job_detail_shell(static_ui_env):
    """A real job id must open the job detail shell, not the home page."""
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/jobs/abc123def456/")
        assert resp.status_code == 200
        assert "Job Detail" in resp.text
        assert "StreamClip UI" not in resp.text


@pytest.mark.asyncio
async def test_static_ui_serves_nested_dynamic_clips_shell(static_ui_env):
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/jobs/abc123def456/clips/")
        assert resp.status_code == 200
        assert "Job Clips" in resp.text


def test_resolve_spa_html_prefers_literal_then_dynamic(static_ui_env):
    from backend.static_ui import resolve_spa_html

    root = static_ui_env
    assert resolve_spa_html(root, "jobs") == root / "jobs" / "index.html"
    assert resolve_spa_html(root, "jobs/xyz") == root / "jobs" / "_" / "index.html"
    assert (
        resolve_spa_html(root, "jobs/xyz/clips")
        == root / "jobs" / "_" / "clips" / "index.html"
    )
    assert resolve_spa_html(root, "totally/unknown/path") is None


@pytest.mark.asyncio
async def test_static_ui_does_not_shadow_api(static_ui_env):
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_static_ui_does_not_shadow_openapi_docs(static_ui_env):
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        docs = await client.get("/docs")
        assert docs.status_code == 200
        assert "swagger" in docs.text.lower() or "openapi" in docs.text.lower()
        openapi = await client.get("/openapi.json")
        assert openapi.status_code == 200


@pytest.mark.asyncio
async def test_static_ui_disabled_by_default(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.web, "serve_static", False)
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
        assert resp.status_code == 404


def test_resolve_static_dir_relative_path(tmp_path, monkeypatch):
    ui = tmp_path / "static" / "ui"
    ui.mkdir(parents=True)
    (ui / "index.html").write_text("<html></html>", encoding="utf-8")
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.web, "serve_static", True)
    monkeypatch.setattr(cfg.web, "static_dir", "static/ui")
    with patch("core.ffmpeg_bins.app_root", return_value=tmp_path):
        assert resolve_static_dir(cfg) == ui.resolve()


def test_resolve_static_dir_missing_index(tmp_path, monkeypatch):
    ui = tmp_path / "ui"
    ui.mkdir()
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.web, "serve_static", True)
    monkeypatch.setattr(cfg.web, "static_dir", ui)
    assert resolve_static_dir(cfg) is None


@pytest.mark.asyncio
async def test_static_ui_serves_html_file_and_spa_fallback(static_ui_env):
    (static_ui_env / "about.html").write_text("<html>About</html>", encoding="utf-8")
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        about = await client.get("/about.html")
        assert about.status_code == 200
        assert "About" in about.text
        unknown = await client.get("/never-existed-route")
        assert unknown.status_code == 200
        assert "StreamClip UI" in unknown.text
        reserved = await client.get("/api/does-not-exist")
        assert reserved.status_code == 404
