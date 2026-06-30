"""Prometheus metrics shared by API and Celery workers."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

JOBS_COMPLETED = Counter(
    "streamclip_jobs_completed_total",
    "Jobs reaching a terminal state",
    ["status"],
)
CLIPS_PROCESSED = Counter(
    "streamclip_clips_processed_total",
    "Individual clip render tasks",
    ["status"],
)
CLIP_RENDER_SECONDS = Histogram(
    "streamclip_clip_render_seconds",
    "Wall time for process_clip",
    buckets=(5.0, 15.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1200.0),
)
PIPELINE_STAGE_SECONDS = Histogram(
    "streamclip_pipeline_stage_seconds",
    "Wall time for a pipeline stage task",
    ["stage"],
    buckets=(1.0, 5.0, 15.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0, 3600.0),
)
WEBHOOK_DELIVERIES = Counter(
    "streamclip_webhook_deliveries_total",
    "Job completion webhook delivery attempts",
    ["result"],
)
