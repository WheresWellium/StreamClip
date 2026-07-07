"""Celery tasks for notifications and training-data export (Phase 3).

All tasks run on the ``default`` queue — never block the GPU queue with
email or corpus export I/O.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import structlog

from backend.db.models import BugReport, Job, User
from backend.db.session import db_session
from core.celery_app import celery_app
from core.config import get_settings
from core.notify.email import bug_report_recipient, send_email
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

    async def _load() -> BugReport | None:
        async with db_session() as db:
            return await db.get(BugReport, report_id)

    report = _safe_async(_load())
    if report is None:
        log.warning("bug_report_email_missing_row", report_id=report_id)
        return {"status": "skipped", "reason": "not_found"}

    recipient = bug_report_recipient()
    categories = ", ".join(report.categories or []) or "uncategorized"
    env = json.dumps(report.environment or {}, indent=2)
    body = (
        f"New StreamClip bug report {report.id}\n"
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
    )
    sent = send_email(
        to=recipient,
        subject=f"[StreamClip] Bug report ({report.severity}): {categories}",
        body=body,
    )
    return {"status": "sent" if sent else "skipped", "report_id": report_id}


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
        "Thanks for purchasing StreamClip Pro!\n"
        "\n"
        f"Your license key:\n\n    {license_key}\n"
        "\n"
        "Activate it in the app under Settings → License. The key can be\n"
        "activated on a limited number of machines; keep it private.\n"
        + (f"\nOrder reference: {order_id}\n" if order_id else "")
    )
    sent = send_email(
        to=recipient,
        subject="Your StreamClip Pro license key",
        body=body,
    )
    return {"status": "sent" if sent else "skipped", "order_id": order_id or ""}


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
