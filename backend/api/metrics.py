"""Prometheus metrics endpoint."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories import JobRepository
from backend.db.session import get_db
from core.config import get_settings
from core.pipeline_metrics import (
    CLIP_RENDER_SECONDS,
    CLIPS_PROCESSED,
    JOBS_COMPLETED,
    PUBLISH_DURATION_SECONDS,
    PUBLISH_JOBS_TOTAL,
    VAULT_QUOTA_DENIED_TOTAL,
    VAULT_SAVES_TOTAL,
    WEBHOOK_DELIVERIES,
)
from core.support.metrics import refresh_support_ticket_metrics

log = structlog.get_logger(__name__)

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
    await refresh_support_ticket_metrics(db)
    try:
        from core.celery_app import celery_app

        inspect = celery_app.control.inspect(timeout=1.0)
        active = inspect.active() or {}
        running = sum(len(tasks) for tasks in active.values())
        CELERY_TASKS_IN_PROGRESS.set(running)
    except Exception:
        CELERY_TASKS_IN_PROGRESS.set(0)


@router.get("/metrics")
async def metrics(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    cfg = get_settings()
    key = cfg.observability.metrics_api_key
    if key:
        auth_header = request.headers.get("Authorization", "")
        provided = (
            auth_header.removeprefix("Bearer ").strip()
            or request.headers.get("X-Metrics-Key", "")
        )
        if provided != key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"code": "unauthorized", "message": "Invalid metrics API key."},
            )
    elif cfg.environment != "development":
        # No key configured outside dev: restrict to loopback only.
        client_host = getattr(request.client, "host", "") or ""
        if client_host not in ("127.0.0.1", "::1", "localhost"):
            log.warning(
                "metrics_loopback_only",
                client_host=client_host,
                hint=(
                    "Prometheus in Docker cannot scrape via loopback. "
                    "Set STREAMCLIP_OBSERVABILITY__METRICS_API_KEY for bridge-network access."
                ),
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"code": "forbidden", "message": "Metrics endpoint is restricted. Set STREAMCLIP_OBSERVABILITY__METRICS_API_KEY to enable external access."},
            )
    await _refresh_gauges(db)
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
