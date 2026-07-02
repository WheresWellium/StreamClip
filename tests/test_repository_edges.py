"""Repository branch coverage."""

from __future__ import annotations

import pytest

from backend.db.models import ClipStatus, JobStatus, UserTier
from backend.db.repositories import ClipRepository, JobRepository, UserRepository


@pytest.mark.asyncio
async def test_job_owner_mismatch(db):
    users = UserRepository(db)
    user = await users.create(
        email="edge@test.local", hashed_password="x", tier=UserTier.FREE,
    )
    jobs = JobRepository(db)
    job = await jobs.create(
        owner_id=user.id,
        source_url="https://x",
        status=JobStatus.QUEUED,
        current_stage="q",
        progress=0.0,
        config_snapshot={},
    )
    assert await jobs.get_for_owner(job.id, None) is None
    assert await jobs.get_for_owner(job.id, "other") is None
    await jobs.list_for_owner(user.id, status=JobStatus.QUEUED)
    await jobs.update_status("missing", JobStatus.ERROR)


@pytest.mark.asyncio
async def test_clip_noops(db):
    jobs = JobRepository(db)
    job = await jobs.create(
        owner_id=None,
        source_url="https://x",
        status=JobStatus.QUEUED,
        current_stage="q",
        progress=0.0,
        config_snapshot={},
    )
    clips = ClipRepository(db)
    await clips.update_storage_keys("nope", raw="r")
    await clips.mark_status("nope", ClipStatus.DONE)
    await clips.update_virality("nope", llm_score=1, llm_reason="r", emotion="e", ensemble_score=1)
    await clips.clear_overlays("nope")
    await clips.reset_for_regenerate("nope")
