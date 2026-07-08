"""Prometheus /metrics endpoint."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

import backend.api.metrics as metrics_api
from backend.db.session import get_db
from core.config import get_settings


@pytest.fixture
def metrics_client(app, client):
    async def fake_db():
        session = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = fake_db
    yield client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def metrics_env(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.observability, "metrics_api_key", "")
    monkeypatch.setattr(cfg, "environment", "production")
    monkeypatch.setattr(metrics_api, "get_settings", lambda: cfg)
    return cfg


@pytest.mark.asyncio
async def test_metrics_endpoint(metrics_client, monkeypatch):
    class FakeJobRepo:
        def __init__(self, db) -> None:
            pass

        async def count_active(self):
            return 3

    monkeypatch.setattr(metrics_api, "JobRepository", FakeJobRepo)
    with patch("core.celery_app.celery_app") as celery:
        celery.control.inspect.return_value.active.return_value = {"w1": [{"id": "t1"}]}
        resp = await metrics_client.get("/metrics")

    assert resp.status_code == 200
    assert "streamclip_active_jobs" in resp.text


@pytest.mark.asyncio
async def test_metrics_celery_inspect_failure(metrics_client, monkeypatch):
    class FakeJobRepo:
        def __init__(self, db) -> None:
            pass

        async def count_active(self):
            return 0

    monkeypatch.setattr(metrics_api, "JobRepository", FakeJobRepo)
    with patch("core.celery_app.celery_app") as celery:
        celery.control.inspect.side_effect = OSError("no broker")
        resp = await metrics_client.get("/metrics")

    assert resp.status_code == 200
    assert "streamclip_celery_tasks_in_progress" in resp.text


@pytest.mark.asyncio
async def test_metrics_rejects_invalid_api_key(metrics_client, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.observability, "metrics_api_key", "secret-key")
    monkeypatch.setattr(metrics_api, "get_settings", lambda: cfg)

    resp = await metrics_client.get("/metrics", headers={"X-Metrics-Key": "wrong"})

    assert resp.status_code == 401
    assert resp.json()["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_metrics_accepts_valid_api_key(metrics_client, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.observability, "metrics_api_key", "secret-key")
    monkeypatch.setattr(metrics_api, "get_settings", lambda: cfg)

    class FakeJobRepo:
        def __init__(self, db) -> None:
            pass

        async def count_active(self):
            return 0

    monkeypatch.setattr(metrics_api, "JobRepository", FakeJobRepo)
    with patch("core.celery_app.celery_app") as celery:
        celery.control.inspect.return_value.active.return_value = {}
        resp = await metrics_client.get("/metrics", headers={"Authorization": "Bearer secret-key"})

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_metrics_loopback_only_outside_dev(metrics_env):
    request = SimpleNamespace(
        headers={},
        client=SimpleNamespace(host="172.18.0.5"),
    )
    db = AsyncMock()

    resp = await metrics_api.metrics(request, db=db)

    assert resp.status_code == 403
    assert json.loads(resp.body)["code"] == "forbidden"
