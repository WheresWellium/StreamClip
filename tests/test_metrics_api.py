"""Prometheus /metrics endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

import backend.api.metrics as metrics_api
from backend.db.session import get_db


@pytest.fixture
def metrics_client(app, client):
    async def fake_db():
        session = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = fake_db
    yield client
    app.dependency_overrides.pop(get_db, None)


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
