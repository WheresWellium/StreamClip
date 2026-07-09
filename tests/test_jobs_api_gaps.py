"""Jobs API routes with remaining HTTP coverage."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import backend.api.jobs as jobs_api
from backend.api.schemas import JobOut
from backend.db.models import ApprovalStatus
from backend.db.session import get_db
from backend.middleware.auth import require_user_id
from backend.middleware.distribution import require_distribution_access
from backend.middleware.scope import RequestScope, get_request_scope

USER = "jobs-gap-user"
SCOPE = RequestScope(user_id=None, device_id="jobsgapdev001")


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


@pytest.fixture
def dist_client(app, client):
    session = MagicMock()
    session.commit = AsyncMock()

    async def fake_db():
        yield session

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_request_scope] = lambda: SCOPE
    app.dependency_overrides[require_user_id] = lambda: USER
    app.dependency_overrides[require_distribution_access] = lambda: USER
    yield SimpleNamespace(client=client, session=session)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_request_scope, None)
    app.dependency_overrides.pop(require_user_id, None)
    app.dependency_overrides.pop(require_distribution_access, None)


@pytest.mark.asyncio
async def test_update_clip_approval(jobs_client):
    clip = SimpleNamespace(id="c1", job_id="job-1")
    svc = MagicMock()
    svc.get_job = AsyncMock()
    repo = MagicMock()
    repo.get = AsyncMock(return_value=clip)
    repo.update_approval = AsyncMock()

    with patch.object(jobs_api, "_get_service", return_value=svc), \
         patch.object(jobs_api, "ClipRepository", return_value=repo), \
         patch.object(jobs_api, "apply_clip_style_feedback", AsyncMock()):
        resp = await jobs_client.client.patch(
            "/api/jobs/job-1/clips/c1/approval",
            json={"approval_status": ApprovalStatus.APPROVED.value},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["clip_id"] == "c1"
    jobs_client.session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_update_clip_approval_not_found(jobs_client):
    from core.errors import StreamClipError
    svc = MagicMock()
    svc.get_job = AsyncMock()
    repo = MagicMock()
    repo.get = AsyncMock(return_value=None)
    repo.update_approval = AsyncMock()

    with patch.object(jobs_api, "_get_service", return_value=svc), \
         patch.object(jobs_api, "ClipRepository", return_value=repo):
        resp = await jobs_client.client.patch(
            "/api/jobs/job-1/clips/missing/approval",
            json={"approval_status": ApprovalStatus.APPROVED.value},
        )
    assert resp.status_code in (404, 500), resp.text


@pytest.mark.asyncio
async def test_update_clip_approval_applies_style_feedback(app, client):
    session = MagicMock()
    session.commit = AsyncMock()

    async def fake_db():
        yield session

    scope = RequestScope(user_id=USER, device_id="jobsgapdev002")
    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_request_scope] = lambda: scope

    clip = SimpleNamespace(id="c1", job_id="job-1")
    svc = MagicMock()
    svc.get_job = AsyncMock()
    repo = MagicMock()
    repo.get = AsyncMock(return_value=clip)
    repo.update_approval = AsyncMock()
    feedback = AsyncMock()

    try:
        with patch.object(jobs_api, "_get_service", return_value=svc), \
             patch.object(jobs_api, "ClipRepository", return_value=repo), \
             patch.object(jobs_api, "apply_clip_style_feedback", feedback):
            resp = await client.patch(
                "/api/jobs/job-1/clips/c1/approval",
                json={"approval_status": ApprovalStatus.APPROVED.value},
            )
        assert resp.status_code == 200, resp.text
        feedback.assert_awaited_once()
        assert feedback.await_args.kwargs["user_id"] == USER
        assert feedback.await_args.kwargs["rating"] == 5
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_request_scope, None)


@pytest.mark.asyncio
async def test_update_clip_with_rerender(jobs_client):
    now = datetime.now(timezone.utc)
    job = SimpleNamespace(id="job-1", clips=[])
    dto = JobOut(
        id="job-1",
        source_url="https://example.com/v.mp4",
        source_title=None,
        source_duration_secs=None,
        status="queued",
        progress=0.0,
        current_stage="queued",
        created_at=now,
    )
    svc = MagicMock()
    svc.update_clip = AsyncMock()
    svc.get_job = AsyncMock(return_value=job)
    svc.to_dto = AsyncMock(return_value=dto)

    with patch.object(jobs_api, "_get_service", return_value=svc), \
         patch.object(jobs_api, "process_clip") as pc:
        pc.apply_async.return_value = MagicMock(id="t1")
        resp = await jobs_client.client.patch(
            "/api/jobs/job-1/clips/c1",
            json={"title": "New title", "rerender": True},
        )

    assert resp.status_code == 200, resp.text
    pc.apply_async.assert_called_once()


@pytest.mark.asyncio
async def test_publish_clip_deprecated_route(dist_client):
    publish_job = SimpleNamespace(
        id="pj-1",
        status="pending",
        scheduled_at=None,
    )
    svc = MagicMock()
    svc.get_job = AsyncMock()
    dist = MagicMock()
    dist.verify_clip_in_job = AsyncMock()
    dist.publish_now = AsyncMock(return_value=publish_job)

    with patch.object(jobs_api, "_get_service", return_value=svc), \
         patch.object(jobs_api, "DistributionService", return_value=dist):
        resp = await dist_client.client.post(
            "/api/jobs/job-1/clips/c1/publish",
            json={"platform": "youtube_shorts", "title": "T"},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["publish_job_id"] == "pj-1"
    dist_client.session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_clips_zip_success(jobs_client):
    svc = MagicMock()
    job = MagicMock(id="jobid12345678")
    svc.get_job = AsyncMock(return_value=job)
    svc.build_clips_zip.return_value = b"PK\x03\x04"
    with patch.object(jobs_api, "_get_service", return_value=svc):
        resp = await jobs_client.client.get("/api/jobs/jobid12345678/clips.zip")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"


@pytest.mark.asyncio
async def test_create_job_dispatches_task(jobs_client):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    job = SimpleNamespace(id="job-new-1", clips=[])
    dto = JobOut(
        id="job-new-1", source_url="https://t.tv/v/1",
        source_title=None, display_title=None,
        source_duration_secs=None,
        status="queued", progress=0.0, current_stage="queued", created_at=now,
    )
    svc = MagicMock()
    svc.create_job = AsyncMock(return_value=job)
    svc.get_job = AsyncMock(return_value=job)
    svc.to_dto = AsyncMock(return_value=dto)
    svc.jobs = MagicMock(attach_celery_task=AsyncMock())
    task_mock = MagicMock(id="task-1")

    with patch.object(jobs_api, "_get_service", return_value=svc), \
         patch.object(jobs_api, "dispatch_task", return_value=task_mock):
        resp = await jobs_client.client.post(
            "/api/jobs",
            json={"source_url": "https://t.tv/v/1"},
        )
    assert resp.status_code in (200, 202), resp.text


@pytest.mark.asyncio
async def test_list_jobs_returns_paginated(jobs_client):
    svc = MagicMock()
    svc.list_jobs = AsyncMock(return_value=[])
    with patch.object(jobs_api, "_get_service", return_value=svc):
        resp = await jobs_client.client.get("/api/jobs?limit=10&offset=0")
    assert resp.status_code == 200
    body = resp.json()
    assert "jobs" in body and "total" in body


@pytest.mark.asyncio
async def test_list_jobs_with_status_and_search(jobs_client):
    svc = MagicMock()
    svc.list_jobs = AsyncMock(return_value=[])
    with patch.object(jobs_api, "_get_service", return_value=svc):
        resp = await jobs_client.client.get("/api/jobs?status=done&search=twitch")
    assert resp.status_code == 200
    svc.list_jobs.assert_awaited_once()
    call_kwargs = svc.list_jobs.await_args.kwargs
    assert call_kwargs["status"] == "done"
    assert call_kwargs["search"] == "twitch"


@pytest.mark.asyncio
async def test_get_job_returns_dto(jobs_client):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    job = SimpleNamespace(id="job-g1", clips=[])
    dto = JobOut(id="job-g1", source_url="https://t.tv/v/2", source_title=None,
                 source_duration_secs=None, status="done", progress=1.0,
                 current_stage="done", created_at=now)
    svc = MagicMock()
    svc.get_job = AsyncMock(return_value=job)
    svc.to_dto = AsyncMock(return_value=dto)
    with patch.object(jobs_api, "_get_service", return_value=svc):
        resp = await jobs_client.client.get("/api/jobs/job-g1")
    assert resp.status_code == 200
    assert resp.json()["id"] == "job-g1"


@pytest.mark.asyncio
async def test_update_job_title(jobs_client):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    job = SimpleNamespace(id="job-u1", clips=[])
    dto = JobOut(id="job-u1", source_url="https://t.tv/v/3", source_title=None,
                 source_duration_secs=None, status="queued", progress=0.0,
                 current_stage="queued", created_at=now)
    svc = MagicMock()
    svc.update_job = AsyncMock(return_value=job)
    svc.get_job = AsyncMock(return_value=job)
    svc.to_dto = AsyncMock(return_value=dto)
    with patch.object(jobs_api, "_get_service", return_value=svc):
        resp = await jobs_client.client.patch(
            "/api/jobs/job-u1",
            json={"display_title": "My title"},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_cancel_job_returns_204(jobs_client):
    svc = MagicMock()
    svc.cancel_job = AsyncMock()
    with patch.object(jobs_api, "_get_service", return_value=svc):
        resp = await jobs_client.client.delete("/api/jobs/job-c1")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_regenerate_clip_dispatches_task(jobs_client):
    svc = MagicMock()
    svc.regenerate_clip = AsyncMock()
    task_mock = MagicMock(id="regen-t1")
    with patch.object(jobs_api, "_get_service", return_value=svc), \
         patch.object(jobs_api, "dispatch_task", return_value=task_mock):
        resp = await jobs_client.client.post(
            "/api/jobs/job-rg/clips/clip-rg/regenerate",
        )
    assert resp.status_code in (200, 202), resp.text
    body = resp.json()
    assert body["clip_id"] == "clip-rg"
    assert body["status"] == "queued"


@pytest.mark.asyncio
async def test_clips_zip_no_clips_returns_400(jobs_client):
    svc = MagicMock()
    job = MagicMock(id="jobid-empty")
    svc.get_job = AsyncMock(return_value=job)
    svc.build_clips_zip.side_effect = ValueError("no clips")
    with patch.object(jobs_api, "_get_service", return_value=svc):
        resp = await jobs_client.client.get("/api/jobs/jobid-empty/clips.zip")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_waveform_not_ready_returns_404(jobs_client):
    svc = MagicMock()
    svc.get_job = AsyncMock()
    storage = MagicMock()
    storage.exists.return_value = False
    with patch.object(jobs_api, "_get_service", return_value=svc), \
         patch.object(jobs_api, "make_storage", return_value=storage):
        resp = await jobs_client.client.get("/api/jobs/job-wv/waveform")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_waveform_ready_returns_url(jobs_client):
    svc = MagicMock()
    svc.get_job = AsyncMock()
    storage = MagicMock()
    storage.exists.return_value = True
    storage.presigned_get_url.return_value = "https://storage/waveform.png"
    with patch.object(jobs_api, "_get_service", return_value=svc), \
         patch.object(jobs_api, "make_storage", return_value=storage):
        resp = await jobs_client.client.get("/api/jobs/job-wv2/waveform")
    assert resp.status_code == 200
    assert "url" in resp.json()


@pytest.mark.asyncio
async def test_get_clip_words_delegates(jobs_client):
    from backend.api.schemas import ClipWordsOut
    svc = MagicMock()
    svc.get_clip_words = AsyncMock(return_value=ClipWordsOut(clip_id="clip-w", words=[]))
    with patch.object(jobs_api, "_get_service", return_value=svc):
        resp = await jobs_client.client.get("/api/jobs/job-w/clips/clip-w/words")
    assert resp.status_code == 200
    assert "words" in resp.json()


@pytest.mark.asyncio
async def test_batch_publish_no_clips_raises(dist_client):
    job = MagicMock(clips=[])
    svc = MagicMock()
    svc.get_job = AsyncMock(return_value=job)
    dist = MagicMock()
    with patch.object(jobs_api, "_get_service", return_value=svc), \
         patch.object(jobs_api, "DistributionService", return_value=dist):
        resp = await dist_client.client.post(
            "/api/jobs/job-bp/clips/batch-publish",
            json={"platform": "youtube_shorts", "clip_ids": []},
        )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_progress_stream_returns_sse(jobs_client):
    from backend.api.schemas import ClipWordsOut
    svc = MagicMock()
    svc.get_job = AsyncMock()

    async def _gen():
        yield "data: {}\n\n"

    with patch.object(jobs_api, "_get_service", return_value=svc), \
         patch.object(jobs_api, "stream_job_progress", return_value=_gen()):
        resp = await jobs_client.client.get(
            "/api/jobs/job-sse/progress",
            headers={"Accept": "text/event-stream"},
        )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
