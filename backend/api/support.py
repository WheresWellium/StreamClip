"""
StreamClip — Support API

POST /api/support/bug-reports   — in-app bug report
POST /api/support/beta-feedback — beta tester questions / ideas

Rows persist in ``bug_reports`` first. Operator notification is async on the
``default`` queue: optional SMTP email and/or ``OPS_WEBHOOK_URL`` (Discord,
Slack, Zapier Catch Hook, or a custom agent inbox — never n8n).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import (
    BetaFeedbackOut,
    BetaFeedbackRequest,
    BugReportOut,
    BugReportRequest,
)
from backend.db.repositories import BugReportRepository, JobRepository
from backend.db.session import get_db
from backend.middleware.auth import get_current_user_id, get_device_id
from backend.middleware.rate_limit import rate_limit_request
from core.notify.email import bug_report_email_status
from core.notify.ops_webhook import ops_webhook_status
from core.task_dispatch import dispatch_task
from core.tasks.notify_tasks import send_bug_report_email, send_ops_webhook

router = APIRouter(prefix="/api/support", tags=["support"])

_FEEDBACK_TOPIC_CATEGORY: dict[str, str] = {
    "question": "other",
    "idea": "other",
    "help": "ui",
    "other": "other",
}


def _queue_support_notifications(report_id: str, *, event: str) -> tuple[str, str]:
    email_status = bug_report_email_status()
    if email_status == "queued" and event == "bug_report":
        dispatch_task(send_bug_report_email, args=(report_id,), queue="default")

    ops_status = ops_webhook_status()
    if ops_status == "queued":
        dispatch_task(send_ops_webhook, args=(report_id, event), queue="default")

    return email_status, ops_status


def _feedback_environment(
    body: BetaFeedbackRequest,
    extra: dict[str, str] | None,
) -> dict[str, Any]:
    env: dict[str, Any] = {"kind": "beta_feedback", "topic": body.topic}
    if extra:
        env.update(extra)
    if body.environment:
        env.update(body.environment)
    return env


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

    email_status, ops_status = _queue_support_notifications(report.id, event="bug_report")
    out = BugReportOut.model_validate(report)
    return out.model_copy(
        update={
            "email_notification": email_status,
            "ops_notification": ops_status,
        },
    )


@router.post(
    "/beta-feedback",
    response_model=BetaFeedbackOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_request)],
)
async def submit_beta_feedback(
    body: BetaFeedbackRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[str | None, Depends(get_current_user_id)] = None,
    device_id: Annotated[str | None, Depends(get_device_id)] = None,
) -> BetaFeedbackOut:
    category = _FEEDBACK_TOPIC_CATEGORY.get(body.topic, "other")
    report = await BugReportRepository(db).create(
        user_id=user_id,
        device_id=device_id,
        job_id=None,
        categories=[category],
        severity="low",
        environment=_feedback_environment(body, None),
        message=body.message.strip(),
    )
    await db.commit()

    _, ops_status = _queue_support_notifications(report.id, event="beta_feedback")
    return BetaFeedbackOut(
        id=report.id,
        status=report.status,
        topic=body.topic,
        created_at=report.created_at,
        ops_notification=ops_status,
    )
