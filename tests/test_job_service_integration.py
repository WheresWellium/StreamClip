"""JobService with real DB."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.api.schemas import CreateJobRequest, UploadInitRequest
from backend.db.models import ClipStatus, JobStatus, UserTier
from backend.db.repositories import ClipRepository, JobRepository, UserRepository
from backend.services.job_service import JobService, UploadService
from core.config import get_settings
from core.errors import JobNotFoundError, QuotaExceededError, StreamClipError
from core.storage import LocalStorage


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(tmp_path)


@pytest.mark.asyncio
async def test_create_job_with_upload_key(db, storage, tmp_path):
    cfg = get_settings(reload=True)
    cfg.rate_limit.enabled = False
    svc = JobService(db, cfg, storage)
    job = await svc.create_job(
        CreateJobRequest(source_upload_key="uploads/x.mp4", target_clips=2),
        owner_id=None,
    )
    assert job.source_storage_key == "uploads/x.mp4"


@pytest.mark.asyncio
async def test_quota_exceeded(db, storage):
    cfg = get_settings(reload=True)
    cfg.rate_limit.enabled = True
    cfg.rate_limit.jobs_per_hour = 0
    users = UserRepository(db)
    user = await users.create(email="q@test.local", hashed_password="x", tier=UserTier.FREE)
    user.jobs_used_this_month = 99999
    await db.flush()
    svc = JobService(db, cfg, storage)
    with pytest.raises(QuotaExceededError):
        await svc.create_job(CreateJobRequest(source_url="https://x"), owner_id=user.id)


@pytest.mark.asyncio
async def test_get_cancel_to_dto(db, storage, tmp_path):
    cfg = get_settings(reload=True)
    svc = JobService(db, cfg, storage)
    job = await svc.create_job(CreateJobRequest(source_url="https://x"), owner_id=None)
    storage.upload("clips/f.mp4", b"v")
    clips = ClipRepository(db)
    clip = await clips.create(job_id=job.id, rank=0, start_secs=0, end_secs=1, title="T")
    await clips.update_storage_keys(clip.id, final="clips/f.mp4", thumbnail="clips/f.mp4")
    clip.status = ClipStatus.DONE
    await db.flush()

    full = await svc.get_job(job.id, owner_id=None)
    dto = await svc.to_dto(full)
    assert dto.clips[0].download_url

    with patch("core.celery_app.celery_app.control.revoke") as rev:
        await svc.jobs.attach_celery_task(job.id, "tid")
        await svc.cancel_job(job.id, owner_id=None)
        rev.assert_called_once()

    with pytest.raises(JobNotFoundError):
        await svc.get_job("missing", owner_id=None)


@pytest.mark.asyncio
async def test_regenerate_and_zip(db, storage, tmp_path):
    cfg = get_settings(reload=True)
    svc = JobService(db, cfg, storage)
    job = await svc.create_job(CreateJobRequest(source_url="https://x"), owner_id=None)
    clips = ClipRepository(db)
    clip = await clips.create(job_id=job.id, rank=0, start_secs=0, end_secs=1)
    with pytest.raises(StreamClipError):
        await svc.regenerate_clip(job.id, clip.id, owner_id=None)
    clip.status = ClipStatus.DONE
    clip.final_storage_key = "k"
    storage.upload("k", b"mp4")
    await db.flush()
    job_full = await svc.get_job(job.id, owner_id=None)
    data = svc.build_clips_zip(job_full)
    assert data
    await svc.regenerate_clip(job.id, clip.id, owner_id=None)


@pytest.mark.asyncio
async def test_update_clip_boundaries_and_metadata(db, storage):
    from backend.api.schemas import UpdateClipRequest

    cfg = get_settings(reload=True)
    svc = JobService(db, cfg, storage)
    job = await svc.create_job(CreateJobRequest(source_url="https://x"), owner_id=None)
    clips = ClipRepository(db)
    clip = await clips.create(
        job_id=job.id,
        rank=0,
        start_secs=0,
        end_secs=10,
        title="Original",
        hook="Old hook",
    )
    clip.status = ClipStatus.DONE
    clip.final_storage_key = "clips/final.mp4"
    await db.flush()

    updated = await svc.update_clip(
        job.id,
        clip.id,
        UpdateClipRequest(
            title="Edited title",
            hook="New hook",
            start_secs=2.0,
            end_secs=12.0,
            caption_style="minimal_white",
            reframe_preset="podcast",
            overlay_enabled=False,
            rerender=False,
        ),
        owner_id=None,
    )
    assert updated.title == "Edited title"
    assert updated.hook == "New hook"
    assert updated.start_secs == 2.0
    assert updated.end_secs == 12.0
    assert updated.render_overrides["caption_style"] == "minimal_white"
    assert updated.render_overrides["overlay_enabled"] is False


@pytest.mark.asyncio
async def test_update_clip_rejects_while_processing(db, storage):
    from backend.api.schemas import UpdateClipRequest

    cfg = get_settings(reload=True)
    svc = JobService(db, cfg, storage)
    job = await svc.create_job(CreateJobRequest(source_url="https://x"), owner_id=None)
    clips = ClipRepository(db)
    clip = await clips.create(job_id=job.id, rank=0, start_secs=0, end_secs=5)
    clip.status = ClipStatus.PROCESSING
    await db.flush()

    with pytest.raises(StreamClipError):
        await svc.update_clip(
            job.id,
            clip.id,
            UpdateClipRequest(start_secs=1.0, end_secs=4.0),
            owner_id=None,
        )


@pytest.mark.asyncio
async def test_upload_service(storage):
    cfg = get_settings(reload=True)
    us = UploadService(cfg, storage)
    resp = await us.init_upload(
        UploadInitRequest(filename="my video!.mp4", content_type="video/mp4"),
        owner_id=None,
    )
    assert resp.storage_key.startswith("uploads/anonymous/")

