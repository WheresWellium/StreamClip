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

import inspect
import json
import time
from typing import Any

import redis
import structlog
from celery import Celery, Task
from celery.signals import task_failure, task_prerun, task_postrun, task_retry

from core.config import get_settings
from core.errors import StreamClipError, clip_failure_message
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


def _init_worker_sentry() -> None:
    """Capture Celery task failures in Sentry when DSN is configured."""
    if not cfg.observability.sentry_dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=cfg.observability.sentry_dsn,
            environment=cfg.environment,
            integrations=[CeleryIntegration(), SqlalchemyIntegration()],
            traces_sample_rate=0.1,
        )
        log.info("sentry_worker_initialised")
    except ImportError:
        log.warning("sentry_sdk_not_installed_on_worker")


_init_worker_sentry()


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

    # Beat schedule (periodic cleanup + autonomous stack health)
    beat_schedule={
        "cleanup-expired-jobs": {
            "task": "core.tasks.pipeline_tasks.cleanup_expired_jobs",
            "schedule": 3600.0,  # every hour
        },
        "process-due-scheduled-publishes": {
            "task": "core.tasks.publish_tasks.process_due_scheduled_jobs",
            "schedule": 60.0,  # every minute
        },
        "probe-stack-health-ops": {
            "task": "core.tasks.notify_tasks.probe_stack_health_ops_alert",
            "schedule": 300.0,  # every 5 minutes — OPS_WEBHOOK stack_degraded
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

    def _job_id_from_call(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str | None:
        """Best-effort ``job_id`` for the failing call, so on_failure can mark
        the right job errored. Reads the kwarg first, else maps positional args
        onto the task signature (skipping the bound ``self``)."""
        if isinstance(kwargs.get("job_id"), str):
            return kwargs["job_id"]
        try:
            params = [
                name
                for name in inspect.signature(self.run).parameters
                if name not in ("self", "cls")
            ]
        except (TypeError, ValueError):
            return None
        for name, value in zip(params, args):
            if name == "job_id" and isinstance(value, str):
                return value
        return None

    def on_failure(
        self,
        exc: BaseException,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,
    ) -> None:
        """Mark the job errored when a stage fails terminally.

        Without this, an unexpected (non-``StreamClipError``) exception left the
        job hung forever — the stages only self-report ``StreamClipError``. This
        is the single place both the Celery worker (after retries) and the
        desktop in-process worker converge on to surface failures to the UI.
        """
        try:
            job_id = self._job_id_from_call(args, kwargs)
            if not job_id:
                return
            # Lazy import: pipeline_tasks imports this module, so a top-level
            # import here would be circular. The module is loaded by call time.
            from core.tasks.pipeline_tasks import _mark_error

            if isinstance(exc, StreamClipError):
                _mark_error(job_id, exc.code, exc.user_message)
            else:
                _mark_error(job_id, "internal_error", clip_failure_message(exc))
        except Exception:  # never let failure-handling raise
            log.error("on_failure_mark_error_failed", task=self.name, exc_info=True)


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
    if cfg.observability.sentry_dsn:
        try:
            import sentry_sdk

            sentry_sdk.capture_exception(exception)
        except ImportError:
            pass


@task_retry.connect
def _on_task_retry(task_id: str, reason: Any, **_: Any) -> None:
    log.warning("celery_task_retry", task_id=task_id, reason=str(reason))
