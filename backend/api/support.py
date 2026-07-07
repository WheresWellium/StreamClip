"""
StreamClip — Support API

POST /api/support/bug-reports — submit an in-app bug report. The row is
persisted first, then an email notification is enqueued on the Celery
``default`` queue (handler never blocks on SMTP).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import BugReportOut, BugReportRequest
from backend.db.repositories import BugReportRepository, JobRepository
from backend.db.session import get_db
from backend.middleware.auth import get_current_user_id, get_device_id
from backend.middleware.rate_limit import rate_limit_request
from core.tasks.notify_tasks import send_bug_report_email

router = APIRouter(prefix="/api/support", tags=["support"])


@router.post(
    "/bug-reports",
    response_model=BugReportOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_request)],
)
async def submit_bug_report(
    body: BugReportRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[str | None, Depends(get_current_user_id)] = None,
    device_id: Annotated[str | None, Depends(get_device_id)] = None,
) -> BugReportOut:
    # Only reference jobs that actually exist (form may carry a stale id)
    job_id = body.job_id
    if job_id is not None and await JobRepository(db).get(job_id) is None:
        job_id = None

    report = await BugReportRepository(db).create(
        user_id=user_id,
        device_id=device_id,
        job_id=job_id,
        categories=body.categories,
        severity=body.severity,
        environment=body.environment,
        message=body.message.strip(),
    )
    await db.commit()

    send_bug_report_email.apply_async(args=[report.id], queue="default")
    return BugReportOut.model_validate(report)
