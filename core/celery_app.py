"""
StreamClip — Celery Application

The single source of truth for our Celery configuration. Imported by both
the FastAPI gateway (which calls `.delay()` to enqueue) and the worker
processes (which actually execute the tasks).

Key production patterns applied:
  • acks_late + reject_on_worker_lost — survive worker crashes mid-task
  • prefetch_multiplier=1 — fair distribution for long GPU jobs
  • worker_max_tasks_per_child — periodic restart releases CUDA memory
  • Task time limits — guaranteed cleanup if a hang occurs
  • Custom task base class that publishes progress to Redis pub/sub
"""

from __future__ import annotations

import json
import time
from typing import Any

import redis
import structlog
from celery import Celery, Task
from celery.signals import task_failure, task_prerun, task_postrun, task_retry

from core.config import get_settings
from core.progress_timing import record_stage_progress, set_eta_context

log = structlog.get_logger(__name__)
cfg = get_settings()

__all__ = [
    "celery_app",
    "get_redis",
    "publish_progress",
    "publish_job_progress",
    "ProgressTask",
    "set_eta_context",
]


# ─── Celery app ──────────────────────────────────────────────────────────────

celery_app = Celery(
    "streamclip",
    broker=cfg.celery.broker_url,
    backend=cfg.celery.result_backend,
    include=[
        "core.tasks.pipeline_tasks",
        "core.tasks.vault_tasks",
        "core.tasks.publish_tasks",
        "core.tasks.notify_tasks",
    ],
)

celery_app.conf.update(
    task_serializer=cfg.celery.task_serializer,
    accept_content=cfg.celery.accept_content,
    timezone=cfg.celery.timezone,
    enable_utc=cfg.celery.enable_utc,
    task_acks_late=cfg.celery.task_acks_late,
    task_reject_on_worker_lost=cfg.celery.task_reject_on_worker_lost,
    worker_prefetch_multiplier=cfg.celery.worker_prefetch_multiplier,
    task_time_limit=cfg.celery.task_time_limit,
    task_soft_time_limit=cfg.celery.task_soft_time_limit,
    result_expires=cfg.celery.result_expires,
    worker_max_tasks_per_child=cfg.celery.worker_max_tasks_per_child,

    # Route tasks to queues by name. GPU work goes to "gpu", everything
    # else to "default". Run two worker pools so the GPU is never blocked
    # by a slow LLM call.
    task_routes={
        "core.tasks.pipeline_tasks.run_transcribe":  {"queue": "gpu"},
        "core.tasks.pipeline_tasks.process_clip":    {"queue": "gpu"},
        "core.tasks.pipeline_tasks.*":               {"queue": "default"},
        "core.tasks.publish_tasks.*":                {"queue": "default"},
        "core.tasks.vault_tasks.*":                  {"queue": "default"},
        "core.tasks.notify_tasks.*":                 {"queue": "default"},
    },

    # Default queue
    task_default_queue="default",

    # Beat schedule (periodic cleanup)
    beat_schedule={
        "cleanup-expired-jobs": {
            "task": "core.tasks.pipeline_tasks.cleanup_expired_jobs",
            "schedule": 3600.0,  # every hour
        },
        "process-due-scheduled-publishes": {
            "task": "core.tasks.publish_tasks.process_due_scheduled_jobs",
            "schedule": 60.0,  # every minute
        },
    },
)


# ─── Progress publisher (Redis pub/sub or in-process bus) ─────────────────────

_redis: redis.Redis | None = None


def _use_memory_progress() -> bool:
    return get_settings().queue.backend == "inprocess"


def get_redis() -> redis.Redis:
    global _redis
    if _use_memory_progress():
        from core.progress_bus import get_progress_bus

        return get_progress_bus().kv  # type: ignore[return-value]
    if _redis is None:
        _redis = redis.from_url(
            cfg.redis.url,
            max_connections=cfg.redis.max_connections,
            decode_responses=True,
        )
    return _redis


def publish_progress(
    job_id: str,
    *,
    stage: str,
    progress: float,
    message: str = "",
    status: str = "processing",
    extra: dict[str, Any] | None = None,
    skip_timing: bool = False,
) -> None:
    """
    Publish a progress event to the Redis channel watched by SSE clients.
    The event is ALSO stored as the channel's latest snapshot so reconnecting
    clients can fetch the current state without waiting for the next publish.
    """
    timing_fields: dict[str, Any] = {}
    if not skip_timing and status == "processing":
        try:
            timing_fields = record_stage_progress(get_redis(), job_id, stage=stage, cfg=cfg)
        except Exception as exc:
            log.warning("progress_timing_failed", job_id=job_id, error=str(exc))

    if _use_memory_progress():
        from core.progress_bus import publish_job_channel

        publish_job_channel(
            cfg,
            job_id,
            stage=stage,
            progress=progress,
            message=message,
            status=status,
            extra=extra,
            timing_fields=timing_fields,
        )
        return

    r = get_redis()
    channel = f"{cfg.redis.pubsub_channel_prefix}{job_id}"
    snapshot_key = f"{channel}:latest"

    payload = {
        "job_id": job_id,
        "stage": stage,
        "progress": round(max(0.0, min(1.0, progress)), 4),
        "message": message,
        "status": status,
        "ts": time.time(),
        **timing_fields,
    }
    if extra:
        payload["extra"] = extra
    seq_key = f"{channel}:seq"
    event_id = r.incr(seq_key)
    r.expire(seq_key, cfg.redis.progress_ttl_secs)
    payload["event_id"] = event_id
    blob = json.dumps(payload)
    r.set(snapshot_key, blob, ex=cfg.redis.progress_ttl_secs)
    r.publish(channel, blob)


def publish_job_progress(
    publish_job_id: str,
    *,
    stage: str,
    progress: float,
    message: str = "",
    status: str = "processing",
    extra: dict[str, Any] | None = None,
) -> None:
    """Publish progress for a distribution publish job (SSE channel)."""
    if _use_memory_progress():
        from core.progress_bus import publish_publish_channel

        publish_publish_channel(
            cfg,
            publish_job_id,
            stage=stage,
            progress=progress,
            message=message,
            status=status,
            extra=extra,
        )
        return

    r = get_redis()
    prefix = cfg.redis.publish_pubsub_channel_prefix
    channel = f"{prefix}{publish_job_id}"
    snapshot_key = f"{channel}:latest"

    payload = {
        "publish_job_id": publish_job_id,
        "stage": stage,
        "progress": round(max(0.0, min(1.0, progress)), 4),
        "message": message,
        "status": status,
        "ts": time.time(),
        **(extra or {}),
    }
    seq_key = f"{channel}:seq"
    event_id = r.incr(seq_key)
    r.expire(seq_key, cfg.redis.progress_ttl_secs)
    payload["event_id"] = event_id
    blob = json.dumps(payload)
    r.set(snapshot_key, blob, ex=cfg.redis.progress_ttl_secs)
    r.publish(channel, blob)


# ─── Progress-aware task base ───────────────────────────────────────────────

class ProgressTask(Task):
    """Base class for tasks that report fine-grained progress to Redis."""

    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    max_retries = 3

    def report(self, job_id: str, *, stage: str, progress: float,
               message: str = "", extra: dict[str, Any] | None = None) -> None:
        publish_progress(
            job_id, stage=stage, progress=progress,
            message=message, status="processing", extra=extra,
        )


# ─── Signal handlers — structured logging for every task lifecycle event ────

@task_prerun.connect
def _on_task_prerun(task_id: str, task: Task, **_: Any) -> None:
    log.info("celery_task_start", task_id=task_id, name=task.name)


@task_postrun.connect
def _on_task_postrun(task_id: str, task: Task, state: str, **_: Any) -> None:
    log.info("celery_task_end", task_id=task_id, name=task.name, state=state)


@task_failure.connect
def _on_task_failure(task_id: str, exception: Exception, task: Task,
                     traceback: Any, einfo: Any, **_: Any) -> None:
    log.error(
        "celery_task_failure",
        task_id=task_id, name=task.name,
        error=str(exception), exc_type=type(exception).__name__,
    )


@task_retry.connect
def _on_task_retry(task_id: str, reason: Any, **_: Any) -> None:
    log.warning("celery_task_retry", task_id=task_id, reason=str(reason))
