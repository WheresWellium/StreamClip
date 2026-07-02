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
PUBLISH_JOBS_TOTAL = Counter(
    "streamclip_publish_jobs_total",
    "Publish job lifecycle events",
    ["status", "platform"],
)
PUBLISH_DURATION_SECONDS = Histogram(
    "streamclip_publish_duration_seconds",
    "Wall time for publish_to_platform worker",
    ["platform"],
    buckets=(1.0, 5.0, 15.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)
VAULT_SAVES_TOTAL = Counter(
    "streamclip_vault_saves_total",
    "Clip Vault copy task outcomes",
    ["status"],
)
VAULT_QUOTA_DENIED_TOTAL = Counter(
    "streamclip_vault_quota_denied_total",
    "Vault save attempts rejected due to tier quota",
)
