"""Celery tasks for social distribution publish plane."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import structlog

from backend.db.models import Clip, PlatformConnection, PublishJob, VaultClip
from backend.db.repositories import PublishJobRepository
from backend.db.session import db_session
from core.celery_app import celery_app, publish_job_progress
from core.config import get_settings
from core.distribution.base import PublishMetadata
from core.distribution.connections import ensure_fresh_credentials
from core.distribution.notify import notify_publish_event, record_publish_outcome
from core.distribution.registry import build_adapter
from core.distribution.tiktok import TikTokAdapter
from core.distribution.youtube import YouTubeShortsAdapter
from core.storage import make_storage
from core.tasks.pipeline_tasks import _safe_async

log = structlog.get_logger(__name__)
cfg = get_settings()


def _report(publish_job_id: str, stage: str, progress: float, message: str = "") -> None:
    publish_job_progress(
        publish_job_id,
        stage=stage,
        progress=progress,
        message=message,
        status="processing",
    )


@celery_app.task(
    name="core.tasks.publish_tasks.publish_to_platform",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
)
def publish_to_platform(self, publish_job_id: str) -> dict[str, str]:
    """Download clip from MinIO and upload to the connected platform."""
    started_at = time.perf_counter()

    async def _terminal_notify(db, job: PublishJob, event: str) -> None:
        refreshed = await db.get(PublishJob, job.id)
        if refreshed is not None:
            await notify_publish_event(db, refreshed, event=event, cfg=cfg)

    async def _do() -> dict[str, str]:
        storage = make_storage(cfg)
        async with db_session() as db:
            repo = PublishJobRepository(db)
            claimed = await repo.claim_for_publish(publish_job_id)
            if claimed is None:
                existing = await repo.get(publish_job_id)
                if existing and existing.status == "published":
                    return {"status": "published", "publish_job_id": publish_job_id}
                return {"status": "skipped", "publish_job_id": publish_job_id}

            job = claimed
            record_publish_outcome(platform=job.platform, status="started")
            _report(publish_job_id, "validate", 0.05, "Validating publish job")

            storage_key = await _resolve_storage_key(db, job)
            if not storage_key or not storage.exists(storage_key):
                await repo.mark_failed(
                    publish_job_id,
                    message="Clip video is missing from storage.",
                    error_code="STORAGE_MISSING",
                )
                publish_job_progress(
                    publish_job_id,
                    stage="error",
                    progress=0.0,
                    message="Clip video is missing from storage.",
                    status="error",
                )
                await _terminal_notify(db, job, "publish.failed")
                record_publish_outcome(
                    platform=job.platform,
                    status="failed",
                    duration_secs=time.perf_counter() - started_at,
                )
                await db.commit()
                return {"status": "failed", "publish_job_id": publish_job_id}

            connection = await db.get(PlatformConnection, job.connection_id)
            if connection is None:
                await repo.mark_failed(
                    publish_job_id,
                    message="Platform connection not found.",
                    error_code="NO_CONNECTION",
                )
                publish_job_progress(
                    publish_job_id,
                    stage="error",
                    progress=0.0,
                    message="Platform connection not found.",
                    status="error",
                )
                await _terminal_notify(db, job, "publish.failed")
                record_publish_outcome(
                    platform=job.platform,
                    status="failed",
                    duration_secs=time.perf_counter() - started_at,
                )
                await db.commit()
                return {"status": "failed", "publish_job_id": publish_job_id}

            _report(publish_job_id, "refresh_token", 0.15, "Refreshing credentials")
            creds = await ensure_fresh_credentials(db, connection)

            metadata = PublishMetadata(
                title=job.title,
                description=job.description,
                tags=[],
            )

            _report(publish_job_id, "download", 0.25, "Downloading clip")
            with tempfile.TemporaryDirectory() as tmp:
                local_video = Path(tmp) / "clip.mp4"
                storage.download(storage_key, local_video)

                adapter = await build_adapter(db, job.platform)

                def on_progress(stage: str, pct: float) -> None:
                    _report(publish_job_id, stage, pct, f"Uploading to {job.platform}")

                if isinstance(adapter, YouTubeShortsAdapter):
                    result = await adapter.upload_video_file(
                        local_video,
                        metadata,
                        creds.access_token,
                        on_progress=on_progress,
                    )
                elif isinstance(adapter, TikTokAdapter):
                    _ = on_progress
                    result = await adapter.publish(storage_key, metadata, creds)
                else:
                    await repo.mark_failed(
                        publish_job_id,
                        message="Unsupported platform adapter.",
                        error_code="unknown_platform",
                    )
                    publish_job_progress(
                        publish_job_id,
                        stage="error",
                        progress=0.0,
                        message="Unsupported platform.",
                        status="error",
                    )
                    await _terminal_notify(db, job, "publish.failed")
                    record_publish_outcome(
                        platform=job.platform,
                        status="failed",
                        duration_secs=time.perf_counter() - started_at,
                    )
                    await db.commit()
                    return {"status": "failed", "publish_job_id": publish_job_id}

            if result.status != "published":
                await repo.mark_failed(
                    publish_job_id,
                    message=result.message or "Platform rejected the upload.",
                    error_code="PLATFORM_REJECTED",
                )
                publish_job_progress(
                    publish_job_id,
                    stage="error",
                    progress=0.0,
                    message=result.message or "Upload failed.",
                    status="error",
                    extra={"external_url": result.external_url},
                )
                await _terminal_notify(db, job, "publish.failed")
                record_publish_outcome(
                    platform=job.platform,
                    status="failed",
                    duration_secs=time.perf_counter() - started_at,
                )
                await db.commit()
                return {"status": "failed", "publish_job_id": publish_job_id}

            external_id = None
            if result.external_url and "/" in result.external_url:
                external_id = result.external_url.rstrip("/").split("/")[-1]

            await repo.mark_published(
                publish_job_id,
                external_id=external_id,
                external_url=result.external_url,
            )
            publish_job_progress(
                publish_job_id,
                stage="published",
                progress=1.0,
                message=result.message or "Published",
                status="done",
                extra={"external_url": result.external_url},
            )
            await _terminal_notify(db, job, "publish.published")
            record_publish_outcome(
                platform=job.platform,
                status="succeeded",
                duration_secs=time.perf_counter() - started_at,
            )
            await db.commit()
            log.info(
                "publish_completed",
                publish_job_id=publish_job_id,
                platform=job.platform,
                external_url=result.external_url,
            )
            return {
                "status": "published",
                "publish_job_id": publish_job_id,
                "external_url": result.external_url or "",
            }

    try:
        return _safe_async(_do())
    except Exception as exc:
        log.exception("publish_task_failed", publish_job_id=publish_job_id, error=str(exc))

        async def _fail() -> None:
            async with db_session() as db:
                repo = PublishJobRepository(db)
                await repo.mark_failed(
                    publish_job_id,
                    message=str(exc)[:500],
                    error_code="WORKER_ERROR",
                )
                job = await repo.get(publish_job_id)
                if job is not None:
                    await notify_publish_event(db, job, event="publish.failed", cfg=cfg)
                    record_publish_outcome(
                        platform=job.platform,
                        status="failed",
                        duration_secs=time.perf_counter() - started_at,
                    )
                await db.commit()

        _safe_async(_fail())
        publish_job_progress(
            publish_job_id,
            stage="error",
            progress=0.0,
            message=str(exc)[:200],
            status="error",
        )
        raise


async def _resolve_storage_key(db, job: PublishJob) -> str | None:
    if job.clip_id:
        clip = await db.get(Clip, job.clip_id)
        return clip.final_storage_key if clip else None
    if job.vault_clip_id:
        vault = await db.get(VaultClip, job.vault_clip_id)
        return vault.storage_key if vault else None
    return None


@celery_app.task(name="core.tasks.publish_tasks.process_due_scheduled_jobs")
def process_due_scheduled_jobs() -> dict[str, list[str]]:
    """Beat task: promote due scheduled publish jobs and enqueue workers."""

    async def _do() -> dict[str, list[str]]:
        async with db_session() as db:
            repo = PublishJobRepository(db)
            due = await repo.list_due_scheduled()
            enqueued: list[str] = []
            for job in due:
                promoted = await repo.promote_scheduled_to_pending(job.id)
                if promoted is not None:
                    publish_to_platform.delay(job.id)
                    enqueued.append(job.id)
            if enqueued:
                await db.commit()
            return {"enqueued": enqueued}

    return _safe_async(_do())
