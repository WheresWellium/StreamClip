---
name: streamclip-distribution-ops
description: >-
  Operates and troubleshoots StreamClip social distribution in production —
  Celery workers, Beat scheduler, MinIO vault storage, OAuth redirect URIs,
  webhooks, and Prometheus metrics. Use when publish jobs stall, OAuth fails,
  scheduled posts miss, env misconfiguration, or writing runbook updates.
---

# StreamClip Distribution Ops

## When to use

- Publish stuck in `pending` or scheduled posts not firing
- OAuth / token / 503 encryption key errors
- Pro gate or approval failures in production
- Webhook delivery or metrics alerting
- Updating operator documentation

**Canonical runbook**: `docs/distribution-runbook.md` — update that file when ops behavior changes; this skill summarizes workflows.

## Runtime components

| Component | Role |
|-----------|------|
| FastAPI `backend/api/distribution.py` | Publish, schedule, OAuth, queue APIs |
| `core/distribution/service.py` | Gates, enqueue, idempotency |
| `core/tasks/publish_tasks.py` | Celery upload worker |
| `process_due_scheduled_jobs` | Beat task (60s) promotes `scheduled` → `pending` |
| Redis | Publish progress pub/sub (`streamclip:publish:{job_id}`) |
| Postgres | `publish_jobs`, `platform_connections`, `vault_clips` |
| MinIO | Job clips + durable `vault/` prefix |

## Required processes

**Worker** (publish now):

```bash
celery -A core.celery_app worker --loglevel=info
```

**Beat** (scheduled publishes — mandatory):

```bash
celery -A core.celery_app beat --loglevel=info
```

Beat schedule: `process_due_scheduled_jobs` every 60 seconds in `core/celery_app.py`.

### Health checks

- `GET /metrics` — `streamclip_celery_tasks_in_progress`, publish counters
- Distribution → Queue tab — pending should move to publishing within seconds
- Logs: `publish_completed`, `publish_task_failed`, `publish_webhook_sent`

## Environment (critical)

```bash
STREAMCLIP_DISTRIBUTION__TOKEN_ENCRYPTION_KEY=<Fernet key>   # 503 if missing
STREAMCLIP_DISTRIBUTION__WEB_ORIGIN=https://your-app.example.com
STREAMCLIP_DISTRIBUTION__YOUTUBE_PUBLISH_ENABLED=true
STREAMCLIP_DISTRIBUTION__TIKTOK_PUBLISH_ENABLED=false
```

Generate Fernet key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Full env table: [reference.md](reference.md).

## OAuth redirect URIs

| Platform | Redirect URI |
|----------|--------------|
| YouTube Shorts | `{WEB_ORIGIN}/api/distribution/oauth/youtube_shorts/callback` |
| TikTok | `{WEB_ORIGIN}/api/distribution/oauth/tiktok/callback` |

**BYO (self-hosted)**: user saves Client ID/Secret in Settings → `install_oauth_apps` table.

**Managed (cloud)**: credentials via env (`YOUTUBE_CLIENT_ID`, etc.); `core/distribution/credentials.py` resolves mode.

## Troubleshooting quick reference

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| 503 on OAuth save | `TOKEN_ENCRYPTION_KEY` unset | Set Fernet key, restart API |
| Pro required | Free tier / no install license | Upgrade or set license |
| Clip not approved | `approval_status` not `approved` | Approve in job UI |
| NO_CONNECTION | No OAuth connection | Distribution → Connections |
| TOKEN_EXPIRED | Refresh failed | Reconnect platform |
| Stuck `pending` | Worker down / Redis | Start worker, check Redis |
| Scheduled missed | Beat not running | Start beat; verify UTC `scheduled_at` |
| STORAGE_MISSING | MinIO key gone | Re-save vault or re-render clip |
| TikTok fails | Flag off or stub adapter | Enable only after API approval |

Detailed flows: `docs/distribution-runbook.md` § Troubleshooting.

## Webhooks & metrics (Phase 5)

Implemented in `core/distribution/notify.py`:

- Signed HMAC webhooks (`X-StreamClip-Signature`) — global + per-user URL
- Prometheus: `streamclip_publish_jobs_total`, `streamclip_publish_duration_seconds`, vault counters

See runbook for event table and alert suggestions.

## Vault retention ops

- Keys: `vault/{user_id}/{vault_clip_id}/` — **excluded** from job retention
- Tier limits: Free 25, Pro 500 (`core/billing.py`)
- Delete vault clip → DB row + MinIO keys removed

## Ops workflow

```
Distribution incident:
- [ ] Confirm worker + beat running
- [ ] Check publish_jobs row (status, scheduled_at, error)
- [ ] Verify TOKEN_ENCRYPTION_KEY + WEB_ORIGIN
- [ ] Check platform connection active
- [ ] Inspect worker logs + /metrics
- [ ] Update docs/distribution-runbook.md if new failure mode
```

## Related

| Resource | Role |
|----------|------|
| [reference.md](reference.md) | Env vars, metrics, log patterns |
| [streamclip-social-distribution](../streamclip-social-distribution/SKILL.md) | Architecture, API |
| `deploy/PRODUCTION.md` | Full stack deploy |
