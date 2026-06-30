"""Prometheus metrics endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories import JobRepository
from backend.db.session import get_db
from core.pipeline_metrics import (
    CLIP_RENDER_SECONDS,
    CLIPS_PROCESSED,
    JOBS_COMPLETED,
    WEBHOOK_DELIVERIES,
)

router = APIRouter(tags=["observability"])
REQUESTS_TOTAL = Counter(
    "streamclip_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_DURATION = Histogram(
    "streamclip_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
ACTIVE_JOBS = Gauge("streamclip_active_jobs", "Jobs not in terminal state")
CELERY_TASKS_IN_PROGRESS = Gauge(
    "streamclip_celery_tasks_in_progress",
    "Celery tasks currently running",
)


async def _refresh_gauges(db: AsyncSession) -> None:
    jobs = JobRepository(db)
    ACTIVE_JOBS.set(await jobs.count_active())
    try:
        from core.celery_app import celery_app

        inspect = celery_app.control.inspect(timeout=1.0)
        active = inspect.active() or {}
        running = sum(len(tasks) for tasks in active.values())
        CELERY_TASKS_IN_PROGRESS.set(running)
    except Exception:
        CELERY_TASKS_IN_PROGRESS.set(0)


@router.get("/metrics")
async def metrics(db: AsyncSession = Depends(get_db)) -> Response:
    await _refresh_gauges(db)
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
