"""Integration tests for backend.db.repositories."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.db.models import (
    Asset,
    Clip,
    ClipStatus,
    Job,
    JobStatus,
    User,
    UserTier,
)
from backend.db.repositories import (
    AssetRepository,
    ClipRepository,
    JobRepository,
    UserRepository,
)


@pytest.mark.asyncio
async def test_job_repository_crud(db):
    jobs = JobRepository(db)
    job = await jobs.create(
        owner_id=None,
        source_url="https://example.com/v",
        status=JobStatus.QUEUED,
        current_stage="queued",
        progress=0.0,
        config_snapshot={},
    )
    assert job.id
    fetched = await jobs.get(job.id)
    assert fetched and fetched.source_url == "https://example.com/v"

    with_clips = await jobs.get(job.id, with_clips=True)
    assert with_clips is not None

    # Anonymous access is device-scoped: no device id → no access
    assert await jobs.get_for_owner(job.id, None) is None
    assert await jobs.get_for_owner(job.id, None, device_scoped=False) is not None
    assert await jobs.get_for_owner(job.id, "other") is None

    job2 = await jobs.create(
        owner_id=None,
        source_url="https://example.com/2",
        status=JobStatus.QUEUED,
        current_stage="queued",
        progress=0.0,
        config_snapshot={},
    )
    listed = await jobs.list_for_owner(None, limit=10)
    assert any(j.id == job2.id for j in listed)

    await jobs.update_status(
        job.id,
        JobStatus.PROCESSING,
        stage="ingest",
        progress=1.5,
        error_code="e",
        error_message="m",
    )
    await db.refresh(job)
    assert job.status == JobStatus.PROCESSING
    assert job.progress == 1.0
    assert job.started_at is not None

    await jobs.update_status(job.id, JobStatus.DONE)
    await db.refresh(job)
    assert job.finished_at is not None

    await jobs.attach_celery_task(job.id, "task-1")
    await db.refresh(job)
    assert job.celery_task_id == "task-1"

    await jobs.cancel(job.id)
    await db.refresh(job)
    assert job.status == JobStatus.CANCELLED

    old = datetime.now(timezone.utc) - timedelta(days=1)
    job2.status = JobStatus.DONE
    await db.flush()
    expired = await jobs.list_expired(old, limit=5)
    assert isinstance(expired, list)

    active = await jobs.count_active()
    assert active >= 0

    await jobs.delete(job.id)
    await db.flush()
    assert await jobs.get(job.id) is None


@pytest.mark.asyncio
async def test_clip_repository(db):
    jobs = JobRepository(db)
    job = await jobs.create(
        owner_id=None,
        source_url="https://x",
        status=JobStatus.QUEUED,
        current_stage="queued",
        progress=0.0,
        config_snapshot={},
    )
    clips = ClipRepository(db)
    clip = await clips.create(
        job_id=job.id,
        rank=0,
        start_secs=0.0,
        end_secs=10.0,
        title="t",
    )
    got = await clips.get(clip.id, with_overlays=True)
    assert got

    listed = await clips.list_for_job(job.id)
    assert len(listed) == 1

    await clips.update_storage_keys(
        clip.id,
        raw="r",
        vertical="v",
        captioned="c",
        final="f",
        thumbnail="th",
    )
    await clips.mark_status(clip.id, ClipStatus.ERROR, error="oops")
    await clips.update_virality(
        clip.id,
        llm_score=1.0,
        llm_reason="r",
        emotion="hype",
        ensemble_score=2.0,
        meme_keywords=["a"],
    )
    c2 = await clips.create(
        job_id=job.id,
        rank=1,
        start_secs=1.0,
        end_secs=2.0,
        ensemble_score=0.5,
    )
    await clips.rerank_by_ensemble(job.id)

    ov = await clips.add_overlay(clip.id, trigger_time_secs=0.0, duration_secs=1.0)
    assert ov.id
    await clips.clear_overlays(clip.id)
    clip.status = ClipStatus.DONE
    clip.final_storage_key = "k"
    await db.flush()
    await clips.reset_for_regenerate(clip.id)
    await db.refresh(clip)
    assert clip.status == ClipStatus.PENDING
    assert clip.final_storage_key is None


@pytest.mark.asyncio
async def test_user_and_asset_repositories(db):
    users = UserRepository(db)
    user = await users.create(
        email=f"u{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )
    assert await users.get_by_email(user.email)
    assert await users.get(user.id)
    await users.increment_jobs_used(user.id)
    await users.increment_minutes_processed(user.id, 5.0)
    await db.refresh(user)
    assert user.jobs_used_this_month >= 1

    assets = AssetRepository(db)
    asset = Asset(
        name="pub",
        asset_type="png",
        storage_key="assets/x",
        description="d",
        is_public=True,
        owner_id=None,
    )
    db.add(asset)
    await db.flush()
    pub = await assets.list_public()
    assert any(a.id == asset.id for a in pub)
    mine = await assets.list_for_user(user.id)
    assert isinstance(mine, list)
    await assets.increment_use_count(asset.id)

