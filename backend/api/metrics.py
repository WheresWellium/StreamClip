"""Prometheus metrics endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

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


@router.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
