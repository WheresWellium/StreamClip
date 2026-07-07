"""Jobs API batch create and remaining HTTP paths."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import backend.api.jobs as jobs_api
from backend.api.schemas import JobOut
from backend.db.session import get_db
from backend.middleware.scope import RequestScope, get_request_scope

SCOPE = RequestScope(user_id=None, device_id="batchjobdev01")


@pytest.fixture
def jobs_client(app, client):
    session = MagicMock()
    session.commit = AsyncMock()

    async def fake_db():
        yield session

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_request_scope] = lambda: SCOPE
    yield SimpleNamespace(client=client, session=session)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_request_scope, None)


@pytest.mark.asyncio
async def test_create_jobs_batch(jobs_client, monkeypatch):
    job = SimpleNamespace(id="job-1")
    now = datetime.now(timezone.utc)
    dto = JobOut(
        id="job-1",
        source_url="https://example.com/a.mp4",
        source_title=None,
        source_duration_secs=None,
        status="queued",
        progress=0.0,
        current_stage="queued",
        created_at=now,
    )

    svc = MagicMock()
    svc.create_job = AsyncMock(return_value=job)
    svc.jobs.attach_celery_task = AsyncMock()
    svc.get_job = AsyncMock(return_value=job)
    svc.to_dto = AsyncMock(return_value=dto)
    task = MagicMock(id="celery-1")

    with patch.object(jobs_api, "_get_service", return_value=svc), \
         patch.object(jobs_api, "start_pipeline") as sp:
        sp.apply_async.return_value = task
        resp = await jobs_client.client.post(
            "/api/jobs/batch",
            json={
                "jobs": [
                    {"source_url": "https://example.com/a.mp4"},
                    {"source_url": "https://example.com/b.mp4"},
                ],
            },
        )

    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert len(body["jobs"]) == 2
    assert svc.create_job.await_count == 2
    jobs_client.session.commit.assert_awaited()
