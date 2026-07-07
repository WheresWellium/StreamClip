"""HTTP coverage for job splice + batch-publish routes."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import backend.api.jobs as jobs_api
from backend.db.session import get_db
from backend.middleware.auth import require_user_id
from backend.middleware.distribution import require_distribution_access
from backend.middleware.scope import RequestScope, get_request_scope

USER = "pub-user-1"
SCOPE = RequestScope(user_id=None, device_id="splicebatchdev01")


@pytest.fixture
def jobs_client(app, client):
    session = MagicMock()
    session.commit = AsyncMock()

    async def fake_db():
        yield session

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_request_scope] = lambda: SCOPE
    yield SimpleNamespace(client=client, session=session, app=app)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_request_scope, None)


@pytest.mark.asyncio
async def test_splice_endpoint_queues_task(jobs_client, monkeypatch):
    clip = SimpleNamespace(id="merge-1")
    svc = MagicMock()
    svc.splice_clips = AsyncMock(return_value=clip)
    delayed: list[tuple] = []

    with patch.object(jobs_api, "_get_service", return_value=svc), \
         patch.object(jobs_api, "splice_clips") as task:
        task.apply_async = MagicMock(side_effect=lambda **kw: delayed.append(kw))
        resp = await jobs_client.client.post(
            "/api/jobs/job-1/clips/splice",
            json={"clip_ids": ["c1", "c2"], "transition": "crossfade"},
        )

    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["clip_id"] == "merge-1"
    assert body["status"] == "queued"
    jobs_client.session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_batch_publish_enqueues(jobs_client, monkeypatch):
    publish_job = SimpleNamespace(
        id="pj-1",
        clip_id="c1",
        vault_clip_id=None,
        platform="youtube_shorts",
        status="pending",
        scheduled_at=None,
        published_at=None,
        external_id=None,
        external_url=None,
        title="T",
        error_message=None,
        last_error_code=None,
        created_at=datetime.now(timezone.utc),
    )

    class FakeDist:
        def __init__(self, db, cfg) -> None:
            pass

        async def publish_now(self, **kwargs):
            return publish_job

    clip = SimpleNamespace(
        id="c1",
        job_id="job-1",
        approval_status="approved",
        final_storage_key="k",
        status="done",
        title="T",
        hook="H",
    )
    job = SimpleNamespace(id="job-1", clips=[clip])

    svc = MagicMock()
    svc.get_job = AsyncMock(return_value=job)

    app = jobs_client.app
    app.dependency_overrides[require_distribution_access] = lambda: USER
    app.dependency_overrides[require_user_id] = lambda: USER

    with patch.object(jobs_api, "_get_service", return_value=svc), \
         patch.object(jobs_api, "DistributionService", FakeDist):
        resp = await jobs_client.client.post(
            "/api/jobs/job-1/clips/batch-publish",
            json={"platform": "youtube_shorts", "clip_ids": ["c1"]},
        )

    app.dependency_overrides.pop(require_distribution_access, None)
    app.dependency_overrides.pop(require_user_id, None)

    assert resp.status_code == 202, resp.text
    assert resp.json()["jobs"][0]["id"] == "pj-1"


@pytest.mark.asyncio
async def test_batch_publish_no_clips_400(jobs_client):
    job = SimpleNamespace(id="job-1", clips=[])
    svc = MagicMock()
    svc.get_job = AsyncMock(return_value=job)

    app = jobs_client.app
    app.dependency_overrides[require_distribution_access] = lambda: USER

    with patch.object(jobs_api, "_get_service", return_value=svc):
        resp = await jobs_client.client.post(
            "/api/jobs/job-1/clips/batch-publish",
            json={"platform": "youtube_shorts", "clip_ids": []},
        )

    app.dependency_overrides.pop(require_distribution_access, None)
    assert resp.status_code == 400
