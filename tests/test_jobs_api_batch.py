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


@pytest.mark.asyncio
async def test_create_job_dispatches_and_attaches_celery(jobs_client):
    job = SimpleNamespace(id="job-create-1")
    now = datetime.now(timezone.utc)
    dto = JobOut(
        id="job-create-1",
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
    handle = MagicMock(id="task-create-1")

    with patch.object(jobs_api, "_get_service", return_value=svc), patch.object(
        jobs_api, "dispatch_task", return_value=handle,
    ) as dispatch:
        resp = await jobs_client.client.post(
            "/api/jobs",
            json={"source_url": "https://example.com/a.mp4", "target_clips": 2},
        )

    assert resp.status_code == 202, resp.text
    assert resp.json()["id"] == "job-create-1"
    dispatch.assert_called_once()
    assert dispatch.call_args.args[0] is jobs_api.start_pipeline
    assert dispatch.call_args.kwargs["args"] == ("job-create-1",)
    svc.jobs.attach_celery_task.assert_awaited_once_with("job-create-1", "task-create-1")
    assert jobs_client.session.commit.await_count >= 2


@pytest.mark.asyncio
async def test_create_jobs_batch_dispatches_via_dispatch_task(jobs_client):
    job = SimpleNamespace(id="job-batch-1")
    now = datetime.now(timezone.utc)
    dto = JobOut(
        id="job-batch-1",
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
    handle = MagicMock(id="task-batch-1")

    with patch.object(jobs_api, "_get_service", return_value=svc), patch.object(
        jobs_api, "dispatch_task", return_value=handle,
    ) as dispatch:
        resp = await jobs_client.client.post(
            "/api/jobs/batch",
            json={"jobs": [{"source_url": "https://example.com/a.mp4"}]},
        )

    assert resp.status_code == 202, resp.text
    dispatch.assert_called_once()
    svc.jobs.attach_celery_task.assert_awaited_once_with("job-batch-1", "task-batch-1")


@pytest.mark.asyncio
async def test_regenerate_clip_uses_dispatch_task(jobs_client):
    svc = MagicMock()
    svc.regenerate_clip = AsyncMock()
    handle = MagicMock(id="regen-1")

    with patch.object(jobs_api, "_get_service", return_value=svc), patch.object(
        jobs_api, "dispatch_task", return_value=handle,
    ) as dispatch:
        resp = await jobs_client.client.post("/api/jobs/job-1/clips/c1/regenerate")

    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["clip_id"] == "c1"
    assert body["status"] == "queued"
    dispatch.assert_called_once()
    assert dispatch.call_args.args[0] is jobs_api.process_clip
    assert dispatch.call_args.kwargs["args"] == ("job-1", "c1")
    assert dispatch.call_args.kwargs["kwargs"] == {"force": True}
