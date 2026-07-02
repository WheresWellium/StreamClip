"""Publish lifecycle notifications (webhooks + metrics helpers)."""

from __future__ import annotations

from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Clip, Job, PublishJob, User, VaultClip
from core.config import Settings, get_settings
from core.pipeline_metrics import PUBLISH_DURATION_SECONDS, PUBLISH_JOBS_TOTAL, WEBHOOK_DELIVERIES
from core.webhooks import deliver_publish_webhook

log = structlog.get_logger(__name__)


def _webhook_creds_from_user(user: User | None) -> tuple[str | None, str | None]:
    if user is None:
        return None, None
    url = user.webhook_url if isinstance(user.webhook_url, str) else None
    secret = user.webhook_secret if isinstance(user.webhook_secret, str) else None
    return url, secret


async def resolve_publish_job_owner_id(db: AsyncSession, job: PublishJob) -> str | None:
    if job.vault_clip_id:
        vault = await db.get(VaultClip, job.vault_clip_id)
        return vault.user_id if vault else None
    if job.clip_id:
        clip = await db.get(Clip, job.clip_id)
        if clip is None:
            return None
        parent = await db.get(Job, clip.job_id)
        return parent.owner_id if parent else None
    return None


async def notify_publish_event(
    db: AsyncSession,
    job: PublishJob,
    *,
    event: str,
    cfg: Settings | None = None,
) -> None:
    """Fire signed publish webhook for terminal or scheduled states."""
    settings = cfg or get_settings()
    owner_id = await resolve_publish_job_owner_id(db, job)
    user = await db.get(User, owner_id) if owner_id else None
    user_url, user_secret = _webhook_creds_from_user(user)

    scheduled_at: str | None = None
    if job.scheduled_at is not None:
        scheduled_at = (
            job.scheduled_at.isoformat()
            if isinstance(job.scheduled_at, datetime)
            else str(job.scheduled_at)
        )

    delivered = deliver_publish_webhook(
        event=event,
        publish_job_id=job.id,
        platform=job.platform,
        status=job.status,
        cfg=settings.webhooks,
        clip_id=job.clip_id,
        vault_clip_id=job.vault_clip_id,
        external_url=job.external_url,
        error_message=job.error_message,
        scheduled_at=scheduled_at,
        user_webhook_url=user_url,
        user_webhook_secret=user_secret,
    )
    WEBHOOK_DELIVERIES.labels(result="success" if delivered else "failure").inc()
    log.info(
        "publish_webhook_sent",
        publish_job_id=job.id,
        webhook_event=event,
        delivered=delivered,
    )


def record_publish_outcome(
    *,
    platform: str,
    status: str,
    duration_secs: float | None = None,
) -> None:
    """Record Prometheus counters/histograms for publish worker outcomes."""
    PUBLISH_JOBS_TOTAL.labels(status=status, platform=platform).inc()
    if duration_secs is not None and status in ("succeeded", "failed"):
        PUBLISH_DURATION_SECONDS.labels(platform=platform).observe(duration_secs)
