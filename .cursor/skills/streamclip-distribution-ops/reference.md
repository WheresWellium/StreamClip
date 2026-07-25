# Distribution Ops — Reference

## Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `STREAMCLIP_DISTRIBUTION__TOKEN_ENCRYPTION_KEY` | Yes (OAuth) | Fernet encrypt for tokens/secrets |
| `STREAMCLIP_DISTRIBUTION__WEB_ORIGIN` | Yes | OAuth redirect base |
| `STREAMCLIP_DISTRIBUTION__YOUTUBE_PUBLISH_ENABLED` | No | Default true |
| `STREAMCLIP_DISTRIBUTION__TIKTOK_PUBLISH_ENABLED` | No | Default false |
| `STREAMCLIP_DISTRIBUTION__YOUTUBE_CLIENT_ID` | Managed | Cloud OAuth |
| `STREAMCLIP_DISTRIBUTION__YOUTUBE_CLIENT_SECRET` | Managed | Cloud OAuth |
| `STREAMCLIP_DISTRIBUTION__TIKTOK_CLIENT_KEY` | Managed | Cloud OAuth |
| `STREAMCLIP_DISTRIBUTION__TIKTOK_CLIENT_SECRET` | Managed | Cloud OAuth |
| `STREAMCLIP_WEBHOOKS__ENABLED` | No | Global webhook delivery |
| `STREAMCLIP_WEBHOOKS__URL` | No | Global webhook endpoint |
| `STREAMCLIP_WEBHOOKS__SECRET` | No | HMAC signing secret |

Config class: `DistributionConfig` in `core/config.py`. API error when key missing: code `distribution_not_configured`, HTTP 503.

## Celery tasks (`core/tasks/publish_tasks.py`)

| Task | Trigger |
|------|---------|
| `publish_to_platform` | Enqueued on publish/schedule/retry |
| `process_due_scheduled_jobs` | Beat every 60s |
| `copy_clip_to_vault` | Save to Clip Vault |

## Redis channels

- Prefix: `streamclip:publish:` (`Settings.distribution.publish_pubsub_channel_prefix`)
- Per-job channel for SSE progress relay

## Prometheus metrics

| Metric | Labels | Meaning |
|--------|--------|---------|
| `streamclip_publish_jobs_total` | `status`, `platform` | started, succeeded, failed, cancelled |
| `streamclip_publish_duration_seconds` | `platform` | Worker wall time |
| `streamclip_vault_saves_total` | `status` | ready / failed |
| `streamclip_vault_quota_denied_total` | — | Tier limit rejections |
| `streamclip_webhook_deliveries_total` | `status` | Webhook outcomes |

Suggested alerts (from runbook):

- `publish_jobs_total{status="failed"}` > 5/hour
- `publish_duration_seconds` p95 > 120s
- `vault_quota_denied_total` spike

## Webhook events

| Event | Payload highlights |
|-------|-------------------|
| `publish.scheduled` | `scheduled_at`, platform, clip refs |
| `publish.published` | `external_url` |
| `publish.failed` | error code/message |
| `publish.cancelled` | — |

Header: `X-StreamClip-Signature: sha256=<hmac>` when secret configured.

## Log patterns to grep

```
publish_completed
publish_task_failed
publish_webhook_sent
process_due_scheduled_jobs
vault_copy_completed
vault_copy_failed
```

## Docker compose services (typical)

| Service | Ops note |
|---------|----------|
| `api` | FastAPI; needs TOKEN_ENCRYPTION_KEY |
| `worker` | Celery default queue — publish tasks |
| `beat` | **Required** for scheduled publishes |
| `redis` | Broker + publish pub/sub |
| `postgres` | publish_jobs, connections, vault_clips |
| `minio` | Clip + vault object storage |

## Token key rotation

1. Generate new Fernet key
2. Deploy new key (existing encrypted tokens become unreadable)
3. Users must reconnect OAuth platforms
4. Document maintenance window in runbook

## MinIO paths

| Prefix | Retention |
|--------|-----------|
| `jobs/{job_id}/` | Subject to job retention policy |
| `vault/{user_id}/` | Durable; not cleaned with job |

## Middleware gates

| Dependency | File | Effect |
|------------|------|--------|
| `require_distribution_access` | `backend/middleware/distribution.py` | Pro or install license |
| `require_user_id` | `backend/middleware/auth.py` | Authenticated user |

Web mirror: `web/lib/distribution/access.ts` → `hasDistributionAccess()`.
