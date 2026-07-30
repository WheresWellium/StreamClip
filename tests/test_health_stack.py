"""Extended health stack endpoint and DB failure branch."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_health_db_failure(app, client):
    from backend.db.session import get_db

    async def fail_db():
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=RuntimeError("db down"))
        yield session

    app.dependency_overrides[get_db] = fail_db
    resp = await client.get("/api/health")
    app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 200
    assert resp.json()["database"] is False


@pytest.mark.asyncio
async def test_health_ollama_failure(client, monkeypatch):
    from core.config import get_settings

    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.llm, "provider", "ollama")
    with patch("httpx.AsyncClient") as hc:
        client_mock = AsyncMock()
        client_mock.get = AsyncMock(side_effect=OSError("down"))
        hc.return_value.__aenter__.return_value = client_mock
        resp = await client.get("/api/health")
    assert resp.json()["ollama"] is False


@pytest.mark.asyncio
async def test_health_stack_includes_worker_check(client, monkeypatch):
    with patch("httpx.Client") as hc:
        inst = hc.return_value.__enter__.return_value
        inst.get.return_value = MagicMock(is_success=True)
        resp = await client.get("/api/health/stack")
    assert resp.status_code == 200
    body = resp.json()
    assert body["worker"] is True
    assert "database" in body["checks"]


@pytest.mark.asyncio
async def test_health_stack_worker_unreachable(client):
    with patch("httpx.Client") as hc:
        hc.return_value.__enter__.return_value.get.side_effect = OSError("no flower")
        resp = await client.get("/api/health/stack")
    assert resp.json()["worker"] is False


@pytest.mark.asyncio
async def test_health_stack_darwin_reports_mps(client):
    with patch("httpx.Client") as hc, patch(
        "core.gpu_profile.is_darwin", return_value=True
    ), patch("core.gpu_profile.mps_available", return_value=True):
        hc.return_value.__enter__.return_value.get.return_value = MagicMock(is_success=True)
        resp = await client.get("/api/health/stack")
    body = resp.json()
    assert body["checks"]["mps"] is True
    assert body["checks"]["cuda"] is False
    assert body["checks"]["nvenc"] is False


@pytest.mark.asyncio
async def test_health_stack_gpu_probe_exception(client):
    with patch("httpx.Client") as hc, patch(
        "core.gpu_profile.is_darwin", side_effect=RuntimeError("probe boom")
    ):
        hc.return_value.__enter__.return_value.get.return_value = MagicMock(is_success=True)
        resp = await client.get("/api/health/stack")
    body = resp.json()
    assert body["checks"]["cuda"] is False
    assert body["checks"]["nvenc"] is False
    assert body["checks"]["mps"] is False


@pytest.mark.asyncio
async def test_health_inprocess_marks_redis_ok(client, monkeypatch):
    from core.config import get_settings

    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["redis"] is True


@pytest.mark.asyncio
async def test_health_stack_with_ollama_in_checks(client, monkeypatch):
    """health_stack passes ollama check into the checks dict when provider=ollama."""
    from core.config import get_settings

    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.llm, "provider", "ollama")
    with patch("httpx.AsyncClient") as ahc, patch("httpx.Client") as hc:
        aclient = AsyncMock()
        aclient.get = AsyncMock(return_value=MagicMock(is_success=True))
        ahc.return_value.__aenter__.return_value = aclient
        inst = hc.return_value.__enter__.return_value
        inst.get.return_value = MagicMock(is_success=True)
        resp = await client.get("/api/health/stack")
    assert resp.status_code == 200
    body = resp.json()
    assert "ollama" in body["checks"]


@pytest.mark.asyncio
async def test_health_all_ok_returns_ok_status(client, monkeypatch):
    """When db, redis (inprocess), and storage all pass the status is 'ok'."""
    from core.config import get_settings

    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")
    with patch("backend.api.health.make_storage") as ms:
        ms.return_value.list_prefix.return_value = []
        resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["redis"] is True
    assert body["storage"] is True
    assert body["status"] == "ok"
