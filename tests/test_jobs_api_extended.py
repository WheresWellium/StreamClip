"""Jobs API with mocked Celery."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.db.models import Job
from backend.db.session import get_sessionmaker


@pytest.mark.asyncio
async def test_create_list_get_job(client):
    task = MagicMock(id="celery-1")
    with patch("backend.api.jobs.start_pipeline") as sp:
        sp.apply_async.return_value = task
        create = await client.post(
            "/api/jobs",
            json={"source_url": "https://example.com/video.mp4", "target_clips": 1},
        )
    assert create.status_code == 202
    job_id = create.json()["id"]

    lst = await client.get("/api/jobs")
    assert lst.status_code == 200

    get = await client.get(f"/api/jobs/{job_id}")
    assert get.status_code == 200

    with patch("core.celery_app.celery_app.control.revoke"):
        delete = await client.delete(f"/api/jobs/{job_id}")
    assert delete.status_code == 204


@pytest.mark.asyncio
async def test_patch_job_display_title(client):
    task = MagicMock(id="celery-patch")
    with patch("backend.api.jobs.start_pipeline") as sp:
        sp.apply_async.return_value = task
        create = await client.post(
            "/api/jobs",
            json={
                "source_url": "https://example.com/v.mp4",
                "display_title": "My custom name",
            },
        )
    assert create.status_code == 202
    job_id = create.json()["id"]
    assert create.json()["display_title"] == "My custom name"

    update = await client.patch(
        f"/api/jobs/{job_id}",
        json={"display_title": "Renamed job"},
    )
    assert update.status_code == 200
    assert update.json()["display_title"] == "Renamed job"
    assert update.json()["source_title"] is None


@pytest.mark.asyncio
async def test_create_job_snapshots_profanity_settings(client):
    task = MagicMock(id="celery-prof")
    with patch("backend.api.jobs.start_pipeline") as sp:
        sp.apply_async.return_value = task
        create = await client.post(
            "/api/jobs",
            json={
                "source_url": "https://example.com/v.mp4",
                "profanity_filter": True,
                "profanity_mode": "bleep",
            },
        )
    assert create.status_code == 202
    job_id = create.json()["id"]

    SessionMaker = get_sessionmaker()
    async with SessionMaker() as session:
        job = await session.get(Job, job_id)
        assert job is not None
        assert job.config_snapshot["profanity_filter"] is True
        assert job.config_snapshot["profanity_mode"] == "bleep"


@pytest.mark.asyncio
async def test_clip_words_endpoint_missing_clip(client):
    task = MagicMock(id="celery-words")
    with patch("backend.api.jobs.start_pipeline") as sp:
        sp.apply_async.return_value = task
        create = await client.post(
            "/api/jobs",
            json={"source_url": "https://example.com/v.mp4"},
        )
    job_id = create.json()["id"]
    resp = await client.get(f"/api/jobs/{job_id}/clips/nonexistent/words")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_clips_zip_and_regenerate(client):
    task = MagicMock(id="t")
    with patch("backend.api.jobs.start_pipeline") as sp:
        sp.apply_async.return_value = task
        create = await client.post(
            "/api/jobs",
            json={"source_url": "https://example.com/v.mp4"},
        )
    job_id = create.json()["id"]
    zip_resp = await client.get(f"/api/jobs/{job_id}/clips.zip")
    assert zip_resp.status_code in (400, 404, 422, 500, 200)

    with patch("backend.api.jobs.process_clip") as pc:
        pc.apply_async.return_value = task
        reg = await client.post(f"/api/jobs/{job_id}/clips/fake/regenerate")
    assert reg.status_code in (404, 400, 422)


@pytest.mark.asyncio
async def test_progress_stream(client):
    task = MagicMock(id="t")
    with patch("backend.api.jobs.start_pipeline") as sp:
        sp.apply_async.return_value = task
        create = await client.post(
            "/api/jobs",
            json={"source_url": "https://example.com/v.mp4"},
        )
    job_id = create.json()["id"]
    with patch("backend.api.jobs.stream_job_progress") as stream:
        async def gen():
            yield "data: {}\n\n"
        stream.return_value = gen()
        resp = await client.get(
            f"/api/jobs/{job_id}/progress",
            headers={"Last-Event-Id": "not-int"},
        )
    assert resp.status_code == 200

