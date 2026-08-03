"""
StreamClip — Support API

POST /api/support/bug-reports   — in-app bug report
POST /api/support/beta-feedback — beta tester questions / ideas
POST /api/support/attachments/init — presigned upload for report attachments

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
    SupportAttachmentInitRequest,
    SupportAttachmentInitResponse,
)
from backend.db.repositories import BugReportRepository, FeedbackAttachmentRepository, JobRepository
from backend.db.session import get_db
from backend.middleware.auth import get_current_user_id, get_device_id
from backend.middleware.rate_limit import rate_limit_request
from core.config import get_settings
from core.errors import StreamClipError
from core.notify.email import bug_report_email_status
from core.notify.ops_webhook import ops_webhook_status
from core.storage import make_storage
from core.support.attachments import (
    MAX_ATTACHMENTS_PER_REPORT,
    support_attachment_key,
)
from core.task_dispatch import dispatch_task
from core.tasks.notify_tasks import send_bug_report_email, send_ops_webhook

router = APIRouter(prefix="/api/support", tags=["support"])

_FEEDBACK_TOPIC_CATEGORY: dict[str, str] = {
    "question": "other",
    "idea": "other",
    "help": "ui",
    "praise": "other",
    "other": "other",
}

_FEEDBACK_AREA_CATEGORY: dict[str, str] = {
    "getting_started": "ui",
    "ingest": "ingest",
    "clipping": "other",
    "captions": "captions",
    "reframe": "reframe",
    "vault": "vault",
    "distribution": "distribution",
    "license_billing": "license_billing",
    "performance": "performance",
    "ui": "ui",
    "other": "other",
}


def _queue_support_notifications(report_id: str, *, event: str) -> tuple[str, str]:
    # Email both bug reports and beta feedback when SMTP is configured (Docker /
    # operator hosts). Desktop installs typically rely on OPS_WEBHOOK_URL → hosted
    # collector instead (see api/support-ingest.py).
    email_status = bug_report_email_status()
    if email_status == "queued" and event in ("bug_report", "beta_feedback"):
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
    "/attachments/init",
    response_model=SupportAttachmentInitResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_request)],
)
async def init_support_attachment(
    body: SupportAttachmentInitRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[str | None, Depends(get_current_user_id)] = None,
    device_id: Annotated[str | None, Depends(get_device_id)] = None,
) -> SupportAttachmentInitResponse:
    if user_id is None and device_id is None:
        raise StreamClipError(
            "Support attachments require user or device scope",
            user_message="Sign in or provide a device id to attach files.",
            code="attachment_scope_required",
            http_status=403,
        )

    owner = user_id or device_id or "anonymous"
    safe_name = "".join(
        c if c.isalnum() or c in "-_." else "_"
        for c in body.filename
    )[:200]

    repo = FeedbackAttachmentRepository(db)
    row = await repo.create_pending(
        user_id=user_id,
        device_id=device_id,
        storage_key="",
        filename=safe_name,
        content_type=body.content_type,
        size_bytes=body.size_bytes,
    )
    key = support_attachment_key(owner, row.id, safe_name)
    row.storage_key = key
    await db.flush()

    cfg = get_settings()
    storage = make_storage(cfg)
    url = storage.presigned_put_url(
        key,
        expires_in=cfg.storage.presigned_expiry_secs,
        content_type=body.content_type,
    )
    await db.commit()
    return SupportAttachmentInitResponse(
        attachment_id=row.id,
        upload_url=url,
        storage_key=key,
        expires_in=cfg.storage.presigned_expiry_secs,
    )


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
    if len(body.attachment_ids) > MAX_ATTACHMENTS_PER_REPORT:
        raise StreamClipError(
            "Too many attachments",
            user_message=f"At most {MAX_ATTACHMENTS_PER_REPORT} attachments per report.",
            code="too_many_attachments",
            http_status=400,
        )

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

    if body.attachment_ids:
        try:
            await FeedbackAttachmentRepository(db).link_to_report(
                body.attachment_ids,
                report_id=report.id,
                user_id=user_id,
                device_id=device_id,
            )
        except ValueError as exc:
            raise StreamClipError(
                str(exc),
                user_message="One or more attachments could not be linked to this report.",
                code="invalid_attachment",
                http_status=400,
            ) from exc

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
    if body.area and body.area in _FEEDBACK_AREA_CATEGORY:
        category = _FEEDBACK_AREA_CATEGORY[body.area]
    else:
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

    email_status, ops_status = _queue_support_notifications(
        report.id, event="beta_feedback",
    )
    return BetaFeedbackOut(
        id=report.id,
        status=report.status,
        topic=body.topic,
        created_at=report.created_at,
        ops_notification=ops_status,
        email_notification=email_status,
    )
