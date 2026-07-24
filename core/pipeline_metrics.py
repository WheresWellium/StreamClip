"""Prometheus metrics shared by API and Celery workers."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

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
    ["reason"],
)
CAPTION_EXPORT_TOTAL = Counter(
    "streamclip_caption_export_total",
    "Caption file exports via API",
    ["format", "status"],
)
TITLE_SUGGESTIONS_TOTAL = Counter(
    "streamclip_title_suggestions_total",
    "Title suggestion API calls",
    ["status"],
)
SUPPORT_TICKETS_OPEN = Gauge(
    "streamclip_support_tickets_open",
    "Open support tickets",
    ["severity"],
)
SUPPORT_TICKET_AGE_SECONDS = Histogram(
    "streamclip_support_ticket_age_seconds",
    "Age of open support tickets in seconds",
    ["severity"],
    buckets=(3600.0, 14400.0, 28800.0, 86400.0, 172800.0, 604800.0, 1209600.0),
)
CONFIDENCE_RERUN_TOTAL = Counter(
    "streamclip_confidence_rerun_total",
    "Low-confidence transcript re-run attempts",
    ["outcome"],
)
TRANSCRIBE_WER_ESTIMATE = Gauge(
    "streamclip_transcribe_wer_estimate",
    "Proxy WER estimate from low-confidence word share",
    ["tier"],
)
CAPTION_PREVIEW_SECONDS = Histogram(
    "streamclip_caption_preview_seconds",
    "Wall time for grouped caption preview API paths",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0),
)
