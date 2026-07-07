"""JobService paths not covered by test_job_service_integration."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.api.schemas import CreateJobRequest, UpdateClipRequest
from backend.db.models import ClipStatus, JobStatus, UserTier
from backend.middleware.scope import RequestScope
from backend.services.job_service import JobService
from core.config import get_settings
from core.errors import InvalidSourceError, JobNotFoundError, QuotaExceededError, StreamClipError


def _svc(db=None):
    db = db or AsyncMock()
    cfg = get_settings(reload=True)
    storage = MagicMock()
    storage.presigned_get_url = MagicMock(return_value="https://cdn/x")
    return JobService(db, cfg, storage), db, cfg, storage


@pytest.mark.asyncio
async def test_create_job_with_upload_key_and_device():
    svc, db, cfg, _ = _svc()
    device_repo = MagicMock()
    device_repo.upsert = AsyncMock(return_value=SimpleNamespace(id="devnorm"))
    svc.devices = device_repo
    svc.jobs.create = AsyncMock(return_value=SimpleNamespace(id="j1"))
    scope = RequestScope(user_id=None, device_id="my-device-id")
    job = await svc.create_job(
        CreateJobRequest(source_upload_key="uploads/x.mp4", target_clips=2),
        scope,
    )
    assert job.id == "j1"
    device_repo.upsert.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_job_quota_exceeded():
    svc, _, cfg, _ = _svc()
    cfg.rate_limit.enabled = True
    user = SimpleNamespace(
        id="u1", tier=UserTier.FREE, jobs_used_this_month=9999,
    )
    svc.users.get = AsyncMock(return_value=user)
    svc.jobs.create = AsyncMock()
    scope = RequestScope(user_id="u1", device_id=None)
    with pytest.raises(QuotaExceededError):
        await svc.create_job(
            CreateJobRequest(source_url="https://example.com/v.mp4"),
            scope,
        )


@pytest.mark.asyncio
async def test_create_job_target_clips_quota():
    svc, _, cfg, _ = _svc()
    cfg.rate_limit.enabled = True
    user = SimpleNamespace(id="u1", tier=UserTier.FREE, jobs_used_this_month=0)
    svc.users.get = AsyncMock(return_value=user)
    svc.jobs.create = AsyncMock()
    scope = RequestScope(user_id="u1", device_id=None)
    with patch("backend.services.job_service.get_tier_limits") as limits:
        limits.return_value = SimpleNamespace(max_jobs_per_month=100, max_target_clips=3)
        with pytest.raises(QuotaExceededError):
            await svc.create_job(
                CreateJobRequest(source_url="https://x", target_clips=10),
                scope,
            )


@pytest.mark.asyncio
async def test_get_job_not_found():
    svc, _, _, _ = _svc()
    svc.jobs.get_for_scope = AsyncMock(return_value=None)
    with pytest.raises(JobNotFoundError):
        await svc.get_job("missing", scope=RequestScope(user_id="u1", device_id=None))


@pytest.mark.asyncio
async def test_cancel_job_revokes_celery():
    svc, _, _, _ = _svc()
    job = SimpleNamespace(id="j1", celery_task_id="celery-task-1")
    svc.jobs.get_for_scope = AsyncMock(return_value=job)
    svc.jobs.cancel = AsyncMock()
    with patch("core.celery_app.celery_app") as celery:
        await svc.cancel_job("j1", scope=RequestScope(user_id="u1", device_id=None))
        celery.control.revoke.assert_called_once_with("celery-task-1", terminate=True)


@pytest.mark.asyncio
async def test_regenerate_clip_errors():
    svc, _, _, _ = _svc()
    clip = SimpleNamespace(id="c1", status=ClipStatus.PENDING)
    job = SimpleNamespace(id="j1", clips=[clip])
    svc.get_job = AsyncMock(return_value=job)
    svc.clips.reset_for_regenerate = AsyncMock()
    with pytest.raises(StreamClipError) as exc:
        await svc.regenerate_clip("j1", "c1", scope=RequestScope(user_id="u1", device_id=None))
    assert exc.value.code == "clip_not_ready"

    clip_done = SimpleNamespace(id="c2", status=ClipStatus.DONE)
    job2 = SimpleNamespace(id="j1", clips=[clip_done])
    svc.get_job = AsyncMock(return_value=job2)
    out = await svc.regenerate_clip("j1", "c2", scope=RequestScope(user_id="u1", device_id=None))
    assert out == "c2"


@pytest.mark.asyncio
async def test_update_clip_validation():
    svc, db, _, _ = _svc()
    clip = SimpleNamespace(
        id="c1", start_secs=0.0, end_secs=10.0, status=ClipStatus.DONE,
        render_overrides={}, hook="h",
    )
    job = SimpleNamespace(id="j1", clips=[clip], config_snapshot={})
    svc.get_job = AsyncMock(return_value=job)
    svc.clips.update_boundaries = AsyncMock()
    svc.clips.reset_for_regenerate = AsyncMock()
    svc.clips.get = AsyncMock(return_value=clip)

    with pytest.raises(StreamClipError):
        await svc.update_clip(
            "j1", "c1",
            UpdateClipRequest(start_secs=5.0, end_secs=5.0),
            scope=RequestScope(user_id="u1", device_id=None),
        )

    clip_proc = SimpleNamespace(
        id="c1", start_secs=0.0, end_secs=10.0, status=ClipStatus.PROCESSING,
        render_overrides={}, hook="h",
    )
    job2 = SimpleNamespace(id="j1", clips=[clip_proc], config_snapshot={})
    svc.get_job = AsyncMock(return_value=job2)
    with pytest.raises(StreamClipError):
        await svc.update_clip(
            "j1", "c1",
            UpdateClipRequest(title="New"),
            scope=RequestScope(user_id="u1", device_id=None),
        )


@pytest.mark.asyncio
async def test_update_clip_not_found_and_clears_transcript_edits():
    svc, _, _, _ = _svc()
    job = SimpleNamespace(id="j1", clips=[], config_snapshot={})
    svc.get_job = AsyncMock(return_value=job)
    with pytest.raises(StreamClipError) as exc:
        await svc.update_clip(
            "j1", "missing",
            UpdateClipRequest(title="x"),
            scope=RequestScope(user_id="u1", device_id=None),
        )
    assert exc.value.code == "clip_not_found"

    clip = SimpleNamespace(
        id="c1", start_secs=0.0, end_secs=10.0, status=ClipStatus.DONE,
        render_overrides={"transcript_edits": {"0": "hi"}}, hook="h",
    )
    job2 = SimpleNamespace(id="j1", clips=[clip], config_snapshot={})
    svc.get_job = AsyncMock(return_value=job2)
    svc.clips.update_boundaries = AsyncMock()
    svc.clips.get = AsyncMock(return_value=clip)
    await svc.update_clip(
        "j1", "c1",
        UpdateClipRequest(transcript_edits={}, rerender=False),
        scope=RequestScope(user_id="u1", device_id=None),
    )
    overrides = svc.clips.update_boundaries.call_args.kwargs["render_overrides"]
    assert "transcript_edits" not in overrides


@pytest.mark.asyncio
async def test_upload_init_audio_disabled():
    from backend.api.schemas import UploadInitRequest
    from backend.services.job_service import UploadService

    svc = UploadService(get_settings(), MagicMock())
    cfg = svc.cfg
    old = cfg.features.audio_ingest
    cfg.features.audio_ingest = False
    try:
        with pytest.raises(StreamClipError) as exc:
            await svc.init_upload(
                UploadInitRequest(filename="pod.mp3", content_type="audio/mpeg"),
                RequestScope(user_id="u1", device_id=None),
            )
        assert exc.value.code == "audio_ingest_disabled"
    finally:
        cfg.features.audio_ingest = old


@pytest.mark.asyncio
async def test_splice_clips_errors():
    svc, db, _, _ = _svc()
    job = SimpleNamespace(
        id="j1",
        clips=[
            SimpleNamespace(id="c1", kind="clip", status=ClipStatus.DONE, final_storage_key="k"),
        ],
        config_snapshot={"aspect_ratio": "9:16"},
    )
    svc.get_job = AsyncMock(return_value=job)
    with pytest.raises(StreamClipError):
        await svc.splice_clips("j1", ["c1"], scope=RequestScope(user_id="u1", device_id=None))

    clips = [
        SimpleNamespace(
            id="c1", kind="clip", status=ClipStatus.DONE, final_storage_key="k1",
            start_secs=0, end_secs=5, hook="a", emotion="hype", transcript_text="t",
            rank=0, render_overrides={},
        ),
        SimpleNamespace(
            id="c2", kind="clip", status=ClipStatus.PENDING, final_storage_key=None,
            start_secs=5, end_secs=10, hook="b", emotion="hype", transcript_text="t",
            rank=1, render_overrides={"aspect_ratio": "16:9"},
        ),
    ]
    job2 = SimpleNamespace(id="j1", clips=clips, config_snapshot={"aspect_ratio": "9:16"})
    svc.get_job = AsyncMock(return_value=job2)
    with pytest.raises(StreamClipError):
        await svc.splice_clips("j1", ["c1", "c2"], scope=RequestScope(user_id="u1", device_id=None))


@pytest.mark.asyncio
async def test_to_dto_with_clips_and_publish():
    svc, _, _, storage = _svc()
    from datetime import datetime, timezone

    overlay = SimpleNamespace(
        id="ov1", trigger_time_secs=0.0, duration_secs=1.0,
        position="top", similarity_score=0.5, matched_keyword="k",
        asset_id=None,
    )
    clip = SimpleNamespace(
        id="c1",
        job_id="j1",
        rank=0,
        start_secs=0.0,
        end_secs=10.0,
        title="T",
        hook="H",
        emotion="hype",
        transcript_text="txt",
        llm_reason="r",
        llm_score=0.5,
        audio_score=0.1,
        spectral_score=0.2,
        flow_score=0.3,
        chat_score=0.4,
        ensemble_score=0.6,
        meme_keywords=[],
        status=ClipStatus.DONE,
        approval_status="approved",
        final_storage_key="clips/f.mp4",
        thumbnail_storage_key="clips/t.jpg",
        overlays=[overlay],
        render_overrides={},
        duration_secs=10.0,
        file_size_bytes=100,
        render_time_secs=1.0,
        kind="clip",
        parent_clip_ids=[],
    )
    now = datetime.now(timezone.utc)
    job = SimpleNamespace(
        id="j1",
        source_url="https://x",
        source_title=None,
        source_duration_secs=60.0,
        status=JobStatus.DONE.value,
        progress=1.0,
        current_stage="done",
        error_code=None,
        error_message=None,
        created_at=now,
        started_at=None,
        pipeline_started_at=None,
        finished_at=None,
        stage_durations_json=None,
        config_snapshot={"content_profile": "gaming", "aspect_ratio": "9:16"},
        clips=[clip],
    )
    pj = SimpleNamespace(
        platform="youtube_shorts", status="published", id="pj1", external_url="https://yt",
    )
    svc.publish_jobs.list_for_clip = AsyncMock(return_value=[pj])
    dto = await svc.to_dto(job)
    assert dto.clips[0].download_url
    assert dto.clips[0].publish_statuses
