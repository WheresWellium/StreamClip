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

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import (
    CreateJobRequest,
    JobListItem,
    JobListResponse,
    JobOut,
)
from backend.db.session import get_db
from backend.middleware.auth import get_current_user_id
from backend.middleware.rate_limit import (
    rate_limit_job_creation,
    rate_limit_request,
)
from backend.services.job_service import JobService
from backend.services.sse import stream_job_progress
from core.config import get_settings
from core.storage import make_storage
from core.tasks.pipeline_tasks import start_pipeline

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
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobOut:
    """Create a new pipeline job and queue it for processing."""
    svc = _get_service(db)
    job = await svc.create_job(body, owner_id=user_id)
    await db.commit()    # Flush the job row before Celery picks it up

    # Hand off to Celery — apply_async returns immediately
    task = start_pipeline.apply_async(args=[job.id])
    await svc.jobs.attach_celery_task(job.id, task.id)
    await db.commit()

    # Reload with clips relation for response
    full = await svc.get_job(job.id, owner_id=user_id)
    return await svc.to_dto(full)


# ─── GET /api/jobs ───────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=JobListResponse,
    dependencies=[Depends(rate_limit_request)],
)
async def list_jobs(
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> JobListResponse:
    svc = _get_service(db)
    jobs = await svc.list_jobs(user_id, limit=limit, offset=offset)
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
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobOut:
    svc = _get_service(db)
    job = await svc.get_job(job_id, owner_id=user_id)
    return await svc.to_dto(job)


# ─── DELETE /api/jobs/{job_id} ───────────────────────────────────────────────

@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit_request)],
)
async def cancel_job(
    job_id: str,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    svc = _get_service(db)
    await svc.cancel_job(job_id, owner_id=user_id)


# ─── GET /api/jobs/{job_id}/progress (SSE) ──────────────────────────────────

@router.get(
    "/{job_id}/progress",
    response_class=StreamingResponse,
)
async def progress_stream(
    job_id: str,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
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
    await svc.get_job(job_id, owner_id=user_id)   # raises JobNotFoundError if denied

    cfg = get_settings()
    generator = stream_job_progress(job_id, cfg)

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",   # disable nginx buffering
            "Connection": "keep-alive",
        },
    )
