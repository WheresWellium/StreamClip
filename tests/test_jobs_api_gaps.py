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
