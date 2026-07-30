from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

@pytest.mark.asyncio
async def test_health_degraded_paths(client):
    with patch("backend.api.health.make_storage", side_effect=RuntimeError("s3")):
        resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["storage"] is False

@pytest.mark.asyncio
async def test_health_redis_fail(client):
    with patch("backend.api.health.aioredis.from_url") as fr:
        r = AsyncMock()
        r.ping = AsyncMock(side_effect=OSError("redis"))
        r.close = AsyncMock()
        fr.return_value = r
        resp = await client.get("/api/health")
    assert resp.json()["redis"] is False

@pytest.mark.asyncio
async def test_health_ollama_branch(client, monkeypatch):
    from core.config import get_settings
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.llm, "provider", "ollama")
    with patch("httpx.AsyncClient") as hc:
        client_mock = AsyncMock()
        client_mock.get = AsyncMock(return_value=MagicMock(is_success=True))
        hc.return_value.__aenter__.return_value = client_mock
        resp = await client.get("/api/health")
    assert "ollama" in resp.json()
