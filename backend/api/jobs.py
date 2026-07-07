"""
StreamClip — Job API Router

REST endpoints:
  POST   /api/jobs                    — Create a new pipeline job
  GET    /api/jobs                    — List user's jobs
  GET    /api/jobs/{job_id}           — Get a single job + clips
  DELETE /api/jobs/{job_id}           — Cancel + delete a job
  GET    /api/jobs/{job_id}/progress  — Server-Sent Events progress stream
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import (
    BatchCreateJobRequest,
    BatchCreateJobResponse,
    BatchPublishClipsRequest,
    BatchPublishClipsResponse,
    ClipApprovalRequest,
    ClipApprovalResponse,
    ClipWordsOut,
    CreateJobRequest,
    JobListItem,
    JobListResponse,
    JobOut,
    PublishClipRequest,
    PublishClipResponse,
    PublishJobOut,
    RegenerateClipResponse,
    SpliceClipsRequest,
    SpliceClipsResponse,
    UpdateClipRequest,
    UpdateJobRequest,
)
from backend.db.models import ApprovalStatus
from backend.db.repositories import ClipRepository
from backend.db.session import get_db
from backend.middleware.auth import require_user_id
from backend.middleware.distribution import require_distribution_access
from backend.middleware.scope import RequestScope, get_request_scope
from backend.middleware.rate_limit import (
    rate_limit_job_creation,
    rate_limit_request,
)
from backend.services.feedback_service import (
    APPROVAL_IMPLICIT_RATING,
    apply_clip_style_feedback,
)
from backend.services.job_service import JobService
from backend.services.sse import stream_job_progress
from core.config import get_settings
from core.distribution.errors import DuplicateInFlightError
from core.distribution.service import DistributionService
from core.errors import StreamClipError
from core.ingest.waveform import waveform_storage_key
from core.storage import make_storage
from core.task_dispatch import dispatch_task
from core.tasks.pipeline_tasks import process_clip, splice_clips, start_pipeline

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_service(db: AsyncSession) -> JobService:
    cfg = get_settings()
    return JobService(db, cfg, make_storage(cfg))


# ─── POST /api/jobs ──────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=JobOut,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit_job_creation)],
)
async def create_job(
    body: CreateJobRequest,
    scope: Annotated[RequestScope, Depends(get_request_scope)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobOut:
    """Create a new pipeline job and queue it for processing."""
    svc = _get_service(db)
    job = await svc.create_job(body, scope)
    await db.commit()    # Flush the job row before Celery picks it up

    # Hand off to worker — returns immediately
    task = dispatch_task(start_pipeline, args=(job.id,))
    await svc.jobs.attach_celery_task(job.id, task.id)
    await db.commit()

    # Reload with clips relation for response
    full = await svc.get_job(job.id, scope=scope)
    return await svc.to_dto(full)


@router.post(
    "/batch",
    response_model=BatchCreateJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit_job_creation)],
)
async def create_jobs_batch(
    body: BatchCreateJobRequest,
    scope: Annotated[RequestScope, Depends(get_request_scope)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BatchCreateJobResponse:
    svc = _get_service(db)
    results: list[JobOut] = []
    for item in body.jobs:
        job = await svc.create_job(item, scope)
        task = dispatch_task(start_pipeline, args=(job.id,))
        await svc.jobs.attach_celery_task(job.id, task.id)
        full = await svc.get_job(job.id, scope=scope)
        results.append(await svc.to_dto(full))
    await db.commit()
    return BatchCreateJobResponse(jobs=results)


# ─── GET /api/jobs ───────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=JobListResponse,
    dependencies=[Depends(rate_limit_request)],
)
async def list_jobs(
    scope: Annotated[RequestScope, Depends(get_request_scope)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    search: str | None = Query(None),
) -> JobListResponse:
    svc = _get_service(db)
    jobs = await svc.list_jobs(
        scope, limit=limit, offset=offset, status=status, search=search,
    )
    items = [
        JobListItem.model_validate(j).model_copy(update={"clip_count": len(j.clips)})
        for j in jobs
    ]
    return JobListResponse(jobs=items, total=len(items), limit=limit, offset=offset)


# ─── GET /api/jobs/{job_id} ──────────────────────────────────────────────────

@router.get(
    "/{job_id}",
    response_model=JobOut,
    dependencies=[Depends(rate_limit_request)],
)
async def get_job(
    job_id: str,
    scope: Annotated[RequestScope, Depends(get_request_scope)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobOut:
    svc = _get_service(db)
    job = await svc.get_job(job_id, scope=scope)
    return await svc.to_dto(job)


@router.patch(
    "/{job_id}",
    response_model=JobOut,
    dependencies=[Depends(rate_limit_request)],
)
async def update_job(
    job_id: str,
    body: UpdateJobRequest,
    scope: Annotated[RequestScope, Depends(get_request_scope)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobOut:
    """Update editable job fields (e.g. display title)."""
    svc = _get_service(db)
    job = await svc.update_job(job_id, body, scope=scope)
    await db.commit()
    return await svc.to_dto(job)


# ─── DELETE /api/jobs/{job_id} ───────────────────────────────────────────────

@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit_request)],
)
async def cancel_job(
    job_id: str,
    scope: Annotated[RequestScope, Depends(get_request_scope)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    svc = _get_service(db)
    await svc.cancel_job(job_id, scope)


# ─── GET /api/jobs/{job_id}/clips.zip ────────────────────────────────────────

@router.get(
    "/{job_id}/clips.zip",
    dependencies=[Depends(rate_limit_request)],
)
async def download_job_clips_zip(
    job_id: str,
    scope: Annotated[RequestScope, Depends(get_request_scope)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Download all finished clips for a job as a single ZIP archive."""
    svc = _get_service(db)
    job = await svc.get_job(job_id, scope=scope)
    try:
        data = svc.build_clips_zip(job)
    except ValueError as exc:
        from core.errors import StreamClipError
        raise StreamClipError(str(exc), user_message=str(exc)) from exc
    filename = f"streamclip-{job_id[:8]}-clips.zip"
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── POST /api/jobs/{job_id}/clips/{clip_id}/regenerate ──────────────────────

@router.post(
    "/{job_id}/clips/{clip_id}/regenerate",
    response_model=RegenerateClipResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit_request)],
)
async def regenerate_clip(
    job_id: str,
    clip_id: str,
    scope: Annotated[RequestScope, Depends(get_request_scope)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RegenerateClipResponse:
    """Re-render a single clip (captions, reframe, overlays) without re-running the full job."""
    svc = _get_service(db)
    await svc.regenerate_clip(job_id, clip_id, scope=scope)
    await db.commit()
    dispatch_task(process_clip, args=(job_id, clip_id), kwargs={"force": True})
    return RegenerateClipResponse(clip_id=clip_id, job_id=job_id, status="queued")


@router.patch(
    "/{job_id}/clips/{clip_id}",
    response_model=JobOut,
    dependencies=[Depends(rate_limit_request)],
)
async def update_clip(
    job_id: str,
    clip_id: str,
    body: UpdateClipRequest,
    scope: Annotated[RequestScope, Depends(get_request_scope)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobOut:
    svc = _get_service(db)
    await svc.update_clip(job_id, clip_id, body, scope=scope)
    await db.commit()
    if body.rerender:
        dispatch_task(process_clip, args=(job_id, clip_id), kwargs={"force": True})
    job = await svc.get_job(job_id, scope=scope)
    return await svc.to_dto(job)


@router.get(
    "/{job_id}/waveform",
    dependencies=[Depends(rate_limit_request)],
)
async def get_job_waveform(
    job_id: str,
    scope: Annotated[RequestScope, Depends(get_request_scope)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Presigned URL for the source waveform PNG (timeline editor track)."""
    svc = _get_service(db)
    await svc.get_job(job_id, scope=scope)  # ownership check
    cfg = get_settings()
    storage = make_storage(cfg)
    key = waveform_storage_key(job_id)
    if not storage.exists(key):
        raise StreamClipError(
            "Waveform not available",
            user_message="Waveform is not ready yet.",
            code="waveform_not_ready",
            http_status=404,
        )
    url = storage.presigned_get_url(key, expires_in=cfg.storage.presigned_expiry_secs)
    return {"url": url}


@router.get(
    "/{job_id}/clips/{clip_id}/words",
    response_model=ClipWordsOut,
    dependencies=[Depends(rate_limit_request)],
)
async def get_clip_words(
    job_id: str,
    clip_id: str,
    scope: Annotated[RequestScope, Depends(get_request_scope)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClipWordsOut:
    """Caption word list for a clip — index basis for transcript_edits."""
    svc = _get_service(db)
    return await svc.get_clip_words(job_id, clip_id, scope=scope)


@router.post(
    "/{job_id}/clips/splice",
    response_model=SpliceClipsResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit_request)],
)
async def splice_job_clips(
    job_id: str,
    body: SpliceClipsRequest,
    scope: Annotated[RequestScope, Depends(get_request_scope)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SpliceClipsResponse:
    svc = _get_service(db)
    clip = await svc.splice_clips(
        job_id,
        body.clip_ids,
        scope=scope,
        transition=body.transition,
    )
    await db.commit()
    dispatch_task(splice_clips, args=(job_id, clip.id))
    return SpliceClipsResponse(clip_id=clip.id, job_id=job_id, status="queued")


@router.post(
    "/{job_id}/clips/{clip_id}/publish",
    response_model=PublishClipResponse,
    dependencies=[Depends(rate_limit_request)],
    deprecated=True,
)
async def publish_clip(
    job_id: str,
    clip_id: str,
    body: PublishClipRequest,
    user_id: Annotated[str, Depends(require_distribution_access)],
    scope: Annotated[RequestScope, Depends(get_request_scope)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublishClipResponse:
    """Deprecated: use POST /api/distribution/publish (the web UI already does).

    Kept for external API consumers; batch-publish stays on the jobs router.
    """
    svc = _get_service(db)
    await svc.get_job(job_id, scope=scope)
    cfg = get_settings()
    dist = DistributionService(db, cfg)
    await dist.verify_clip_in_job(job_id, clip_id, user_id)
    job = await dist.publish_now(
        user_id=user_id,
        clip_id=clip_id,
        platform=body.platform,
        title=body.title,
        description=body.description,
    )
    await db.commit()
    message = "Queued for publishing" if job.status == "pending" else f"Scheduled for {job.scheduled_at}"
    return PublishClipResponse(
        clip_id=clip_id,
        platform=body.platform,
        status=job.status,
        message=message,
        publish_job_id=job.id,
    )


@router.post(
    "/{job_id}/clips/batch-publish",
    response_model=BatchPublishClipsResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit_request)],
)
async def batch_publish_clips(
    job_id: str,
    body: BatchPublishClipsRequest,
    user_id: Annotated[str, Depends(require_distribution_access)],
    scope: Annotated[RequestScope, Depends(get_request_scope)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BatchPublishClipsResponse:
    svc = _get_service(db)
    job = await svc.get_job(job_id, scope=scope)
    cfg = get_settings()
    dist = DistributionService(db, cfg)

    clip_ids = body.clip_ids
    if not clip_ids:
        clip_ids = [
            c.id
            for c in job.clips
            if c.approval_status == ApprovalStatus.APPROVED.value
            and c.final_storage_key
            and c.status == "done"
        ]

    if not clip_ids:
        raise StreamClipError(
            "No clips to publish",
            user_message="Approve at least one finished clip before batch publishing.",
            code="no_clips",
            http_status=400,
        )

    jobs_out: list[PublishJobOut] = []
    skipped = 0
    for clip_id in clip_ids:
        clip = next((c for c in job.clips if c.id == clip_id), None)
        if clip is None or clip.job_id != job_id:
            skipped += 1
            continue
        try:
            publish_job = await dist.publish_now(
                user_id=user_id,
                clip_id=clip_id,
                platform=body.platform,
                title=body.title or clip.title,
                description=body.description or clip.hook,
            )
            jobs_out.append(PublishJobOut.model_validate(publish_job))
        except DuplicateInFlightError:
            skipped += 1

    if not jobs_out:
        raise StreamClipError(
            "Batch publish failed",
            user_message="No clips were queued. They may already be publishing.",
            code="batch_empty",
            http_status=409,
        )

    await db.commit()
    return BatchPublishClipsResponse(jobs=jobs_out, skipped=skipped)


@router.patch(
    "/{job_id}/clips/{clip_id}/approval",
    response_model=ClipApprovalResponse,
    dependencies=[Depends(rate_limit_request)],
)
async def update_clip_approval(
    job_id: str,
    clip_id: str,
    body: ClipApprovalRequest,
    scope: Annotated[RequestScope, Depends(get_request_scope)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClipApprovalResponse:
    svc = _get_service(db)
    await svc.get_job(job_id, scope=scope)
    repo = ClipRepository(db)
    clip = await repo.get(clip_id, with_overlays=False)
    if clip is None or clip.job_id != job_id:
        raise StreamClipError("Clip not found", user_message="Clip not found")
    await repo.update_approval(clip_id, body.approval_status)

    # Approve/reject doubles as implicit feedback for style learning
    implicit_rating = APPROVAL_IMPLICIT_RATING.get(body.approval_status)
    if scope.user_id and implicit_rating is not None:
        await apply_clip_style_feedback(
            db, clip=clip, user_id=scope.user_id, rating=implicit_rating,
        )

    await db.commit()
    return ClipApprovalResponse(clip_id=clip_id, approval_status=body.approval_status)


# ─── GET /api/jobs/{job_id}/progress (SSE) ──────────────────────────────────

@router.get(
    "/{job_id}/progress",
    response_class=StreamingResponse,
)
async def progress_stream(
    job_id: str,
    scope: Annotated[RequestScope, Depends(get_request_scope)],
    db: Annotated[AsyncSession, Depends(get_db)],
    last_event_id: Annotated[str | None, Header(alias="Last-Event-Id")] = None,
) -> StreamingResponse:
    """
    Server-Sent Events stream of pipeline progress.

    Event types emitted:
      • `progress` — fired on every state change
      • `done`     — final event when the job completes successfully
      • `error`    — final event on pipeline failure

    Each event's data is a JSON object matching ProgressEvent schema.
    """
    # Authorise: confirm the user can access this job
    svc = _get_service(db)
    await svc.get_job(job_id, scope=scope)   # raises JobNotFoundError if denied

    cfg = get_settings()
    cursor: int | None = None
    if last_event_id:
        try:
            cursor = int(last_event_id)
        except ValueError:
            cursor = None

    generator = stream_job_progress(job_id, cfg, last_event_id=cursor)

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",   # disable nginx buffering
            "Connection": "keep-alive",
        },
    )
