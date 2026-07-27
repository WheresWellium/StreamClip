"""Celery tasks for notifications and training-data export (Phase 3).

All tasks run on the ``default`` queue — never block the GPU queue with
email or corpus export I/O.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import structlog
from sqlalchemy import select

from backend.db.models import BugReport, FeedbackAttachment, Job, User
from backend.db.session import db_session
from core.celery_app import celery_app
from core.config import get_settings
from core.notify.email import bug_report_recipient, send_email
from core.notify.ops_webhook import post_ops_webhook
from core.storage import make_storage
from core.tasks.pipeline_tasks import _safe_async

log = structlog.get_logger(__name__)
cfg = get_settings()


@celery_app.task(
    name="core.tasks.notify_tasks.send_bug_report_email",
    max_retries=2,
    default_retry_delay=30,
)
def send_bug_report_email(report_id: str) -> dict[str, str]:
    """Email the configured recipient about a new bug report."""

    async def _load() -> tuple[BugReport | None, list[FeedbackAttachment]]:
        async with db_session() as db:
            report = await db.get(BugReport, report_id)
            if report is None:
                return None, []
            result = await db.execute(
                select(FeedbackAttachment).where(
                    FeedbackAttachment.bug_report_id == report_id,
                ),
            )
            return report, list(result.scalars().all())

    report, attachments = _safe_async(_load())
    if report is None:
        log.warning("bug_report_email_missing_row", report_id=report_id)
        return {"status": "skipped", "reason": "not_found"}

    recipient = bug_report_recipient()
    categories = ", ".join(report.categories or []) or "uncategorized"
    env = json.dumps(report.environment or {}, indent=2)
    attachment_lines = ""
    if attachments:
        storage = make_storage(cfg)
        ttl = 24 * 3600
        lines = []
        for att in attachments:
            url = storage.presigned_get_url(att.storage_key, expires_in=ttl)
            lines.append(f"  - {att.filename}: {url}")
        attachment_lines = "\nAttachments (24h links):\n" + "\n".join(lines) + "\n"
    body = (
        f"New qClip bug report {report.id}\n"
        f"\n"
        f"Severity:   {report.severity}\n"
        f"Categories: {categories}\n"
        f"User:       {report.user_id or 'anonymous'}\n"
        f"Device:     {report.device_id or '-'}\n"
        f"Job:        {report.job_id or '-'}\n"
        f"Created:    {report.created_at.isoformat()}\n"
        f"\n"
        f"Message:\n{report.message}\n"
        f"\n"
        f"Environment:\n{env}\n"
        f"{attachment_lines}"
    )
    sent = send_email(
        to=recipient,
        subject=f"[qClip] Bug report ({report.severity}): {categories}",
        body=body,
    )
    return {"status": "sent" if sent else "skipped", "report_id": report_id}


def _ops_payload_from_report(report: BugReport, *, event: str) -> dict[str, object]:
    return {
        "event": event,
        "id": report.id,
        "severity": report.severity,
        "categories": report.categories or [],
        "message": report.message,
        "user_id": report.user_id,
        "device_id": report.device_id,
        "job_id": report.job_id,
        "environment": report.environment or {},
        "created_at": report.created_at.isoformat(),
        "app": "streamclip",
    }


@celery_app.task(
    name="core.tasks.notify_tasks.send_ops_webhook",
    max_retries=2,
    default_retry_delay=30,
)
def send_ops_webhook(report_id: str, event: str) -> dict[str, str]:
    """Forward a support row to ``OPS_WEBHOOK_URL`` (Discord/Slack/agent inbox)."""

    async def _load() -> BugReport | None:
        async with db_session() as db:
            return await db.get(BugReport, report_id)

    report = _safe_async(_load())
    if report is None:
        log.warning("ops_webhook_missing_row", report_id=report_id, webhook_event=event)
        return {"status": "skipped", "reason": "not_found"}

    sent = post_ops_webhook(_ops_payload_from_report(report, event=event))
    return {
        "status": "sent" if sent else "skipped",
        "report_id": report_id,
        "event": event,
    }


@celery_app.task(
    name="core.tasks.notify_tasks.send_job_failed_ops_alert",
    max_retries=2,
    default_retry_delay=30,
)
def send_job_failed_ops_alert(
    job_id: str,
    *,
    done_count: int = 0,
    error_count: int = 0,
) -> dict[str, str]:
    """Proactive ops alert when a job finishes with clip errors (before user reports)."""
    sent = post_ops_webhook(
        {
            "event": "job_failed",
            "job_id": job_id,
            "done_count": done_count,
            "error_count": error_count,
            "status": "error",
            "app": "streamclip",
        },
    )
    return {
        "status": "sent" if sent else "skipped",
        "job_id": job_id,
        "event": "job_failed",
    }


@celery_app.task(
    name="core.tasks.notify_tasks.probe_stack_health_ops_alert",
    max_retries=0,
)
def probe_stack_health_ops_alert() -> dict[str, object]:
    """
    Beat task — probe DB/Redis/storage and POST ``stack_degraded`` when unhealthy.

    Cooldown (~15 min) prevents inbox floods during sustained outages. No-op when
    ``OPS_WEBHOOK_URL`` is unset.
    """
    from core.notify.stack_health import probe_stack_dependencies, should_emit_stack_alert

    result = probe_stack_dependencies(cfg)
    status = str(result["status"])
    if status == "ok":
        should_emit_stack_alert("ok")  # reset edge tracking
        return {"status": "ok", "event": "stack_health", "alerted": False}

    if not should_emit_stack_alert(status):
        return {
            "status": status,
            "event": "stack_degraded",
            "alerted": False,
            "reason": "cooldown",
            "checks": result["checks"],
        }

    sent = post_ops_webhook(
        {
            "event": "stack_degraded",
            "status": status,
            "checks": result["checks"],
            "failures": result["failures"][:5],
            "app": "streamclip",
        },
    )
    return {
        "status": status,
        "event": "stack_degraded",
        "alerted": bool(sent),
        "checks": result["checks"],
    }


@celery_app.task(
    name="core.tasks.notify_tasks.send_license_key_email",
    max_retries=3,
    default_retry_delay=60,
)
def send_license_key_email(recipient: str, license_key: str, order_id: str | None) -> dict[str, str]:
    """
    order_created fallback: deliver a locally-generated license key to the
    purchaser. Only used when Lemon Squeezy license keys are not enabled on
    the store (LS delivers keys natively otherwise).
    """
    body = (
        "Thanks for purchasing qClip Studio!\n"
        "\n"
        f"Your license key:\n\n    {license_key}\n"
        "\n"
        "Activate it in the app under Settings → License. The key can be\n"
        "activated on a limited number of machines; keep it private.\n"
        + (f"\nOrder reference: {order_id}\n" if order_id else "")
    )
    sent = send_email(
        to=recipient,
        subject="Your qClip Studio license key",
        body=body,
    )
    return {"status": "sent" if sent else "skipped", "order_id": order_id or ""}


@celery_app.task(
    name="core.tasks.notify_tasks.send_password_reset_email",
    max_retries=2,
    default_retry_delay=30,
)
def send_password_reset_email(recipient: str, reset_url: str) -> dict[str, str]:
    body = (
        "You requested a password reset for your qClip account.\n"
        "\n"
        f"Reset your password:\n{reset_url}\n"
        "\n"
        "This link expires in one hour. If you did not request a reset, "
        "you can ignore this email.\n"
    )
    sent = send_email(
        to=recipient,
        subject="Reset your qClip password",
        body=body,
    )
    return {"status": "sent" if sent else "skipped", "recipient": recipient}


def _anonymize_snapshot(snapshot: dict) -> dict:
    """Strip anything user-identifying from a job config snapshot."""
    return {
        k: v
        for k, v in (snapshot or {}).items()
        if k not in ("source_url", "customer_email")
    }


@celery_app.task(name="core.tasks.notify_tasks.export_training_bundle")
def export_training_bundle(job_id: str) -> dict[str, str]:
    """
    Phase 3c — export an anonymized bundle of a completed job for model
    improvement. Only enqueued when the owner opted in; contains transcripts,
    scores, and config — no emails, URLs, or account identifiers.
    """

    async def _build() -> dict | None:
        async with db_session() as db:
            job = await db.get(Job, job_id)
            if job is None or job.owner_id is None:
                return None
            owner = await db.get(User, job.owner_id)
            if owner is None or not owner.data_contribution_opt_in:
                log.info("training_export_skipped_no_opt_in", job_id=job_id)
                return None
            await db.refresh(job, ["clips"])
            return {
                "job_id": job.id,
                "created_at": job.created_at.isoformat(),
                "source_duration_secs": job.source_duration_secs,
                "config": _anonymize_snapshot(job.config_snapshot or {}),
                "clips": [
                    {
                        "rank": c.rank,
                        "start_secs": c.start_secs,
                        "end_secs": c.end_secs,
                        "emotion": c.emotion,
                        "transcript_text": c.transcript_text,
                        "ensemble_score": c.ensemble_score,
                        "llm_score": c.llm_score,
                        "audio_score": c.audio_score,
                        "spectral_score": c.spectral_score,
                        "flow_score": c.flow_score,
                        "chat_score": c.chat_score,
                        "llm_reason": c.llm_reason,
                    }
                    for c in job.clips
                ],
            }

    bundle = _safe_async(_build())
    if bundle is None:
        return {"status": "skipped", "job_id": job_id}

    storage = make_storage(cfg)
    key = f"training-corpus/{job_id}.json"
    with tempfile.TemporaryDirectory() as tmp:
        local = Path(tmp) / "bundle.json"
        local.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        storage.upload(key, local, content_type="application/json")

    log.info("training_bundle_exported", job_id=job_id, key=key)
    return {"status": "exported", "job_id": job_id, "key": key}
