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
    with patch("httpx.Client") as hc:
        hc.return_value.__enter__.return_value.get.side_effect = OSError("down")
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
