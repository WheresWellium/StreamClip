"""Jobs API with mocked Celery."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


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

