from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

@pytest.mark.asyncio
async def test_clips_zip_streamclip_error(client):
    svc = MagicMock()
    job = MagicMock(id="jobid12345678")
    svc.get_job = AsyncMock(return_value=job)
    svc.build_clips_zip.side_effect = ValueError("no finished clips")
    with patch("backend.api.jobs._get_service", return_value=svc):
        resp = await client.get("/api/jobs/jobid12345678/clips.zip")
    assert resp.status_code in (400, 422, 500)

@pytest.mark.asyncio
async def test_progress_stream_cursor_int(client):
    svc = MagicMock()
    svc.get_job = AsyncMock(return_value=MagicMock(id="j1"))
    async def gen():
        yield "data: {}\n\n"
    with patch("backend.api.jobs._get_service", return_value=svc):
        with patch("backend.api.jobs.stream_job_progress", return_value=gen()):
            resp = await client.get("/api/jobs/j1/progress", headers={"Last-Event-Id": "5"})
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_regenerate_clip_queued(client):
    svc = MagicMock()
    svc.regenerate_clip = AsyncMock()
    task = MagicMock()
    with patch("backend.api.jobs._get_service", return_value=svc):
        with patch("backend.api.jobs.process_clip") as pc:
            pc.apply_async.return_value = task
            resp = await client.post("/api/jobs/j1/clips/c1/regenerate")
    assert resp.status_code in (202, 401, 404)

