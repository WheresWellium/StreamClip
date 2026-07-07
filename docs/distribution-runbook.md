# StreamClip Distribution — Operations Runbook

Operations guide for social publish (YouTube Shorts, TikTok), Clip Vault, Celery workers, and OAuth.

## Architecture overview

| Component | Role |
|-----------|------|
| FastAPI `backend/api/distribution.py` | Publish, schedule, OAuth, queue APIs |
| `core/distribution/service.py` | Gates, enqueue, idempotency |
| `core/tasks/publish_tasks.py` | Celery upload worker |
| `process_due_scheduled_jobs` | Beat task (60s) promotes scheduled → pending |
| Redis | Publish progress pub/sub (`publish:{job_id}`) |
| Postgres | `publish_jobs`, `platform_connections`, `vault_clips` |
| MinIO | Job clips + durable `vault/` prefix |

## Required environment variables

```bash
# Token encryption (required for OAuth connections)
STREAMCLIP_DISTRIBUTION__TOKEN_ENCRYPTION_KEY=<Fernet key>

# OAuth redirect base (must match your web origin)
STREAMCLIP_DISTRIBUTION__WEB_ORIGIN=https://your-app.example.com
```

`docker-compose.yml` (local dev) already sets a hardcoded DEV-ONLY key + `WEB_ORIGIN=http://localhost:3000`
on `api`/`worker`/`gpu-worker` so OAuth connections work out of the box locally — never reuse that key
in production; generate a fresh one per the command above.

```bash

# Platform feature flags
STREAMCLIP_DISTRIBUTION__YOUTUBE_PUBLISH_ENABLED=true
STREAMCLIP_DISTRIBUTION__TIKTOK_PUBLISH_ENABLED=false   # enable when TikTok API approved

# Managed OAuth (Cloud) — optional; BYO uses install_oauth_apps table
STREAMCLIP_DISTRIBUTION__YOUTUBE_CLIENT_ID=
STREAMCLIP_DISTRIBUTION__YOUTUBE_CLIENT_SECRET=
STREAMCLIP_DISTRIBUTION__TIKTOK_CLIENT_ID=
STREAMCLIP_DISTRIBUTION__TIKTOK_CLIENT_SECRET=

# Global webhooks (optional; users can also set per-account webhook URL)
STREAMCLIP_WEBHOOKS__ENABLED=true
STREAMCLIP_WEBHOOKS__URL=https://hooks.example.com/streamclip
STREAMCLIP_WEBHOOKS__SECRET=<hmac secret>
```

Generate a Fernet key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Celery worker and Beat

Publish tasks run on the default Celery worker. Scheduled posts require Beat.

**Worker** (must be running for publish now):

```bash
celery -A core.celery_app worker --loglevel=info
```

**Beat** (required for scheduled publishes):

```bash
celery -A core.celery_app beat --loglevel=info
```

Beat schedule entry: `process_due_scheduled_jobs` every 60 seconds (see `core/celery_app.py`).

### Verify worker health

- `GET /metrics` — check `streamclip_celery_tasks_in_progress`
- Distribution → Queue tab — pending jobs should move to publishing within seconds
- Logs: `publish_completed`, `publish_task_failed`, `publish_webhook_sent`

## OAuth setup

### Self-hosted (BYO)

1. Create Google Cloud / TikTok developer apps.
2. Set redirect URI: `{WEB_ORIGIN}/api/distribution/oauth/{platform}/callback`
   - YouTube: `youtube_shorts`
   - TikTok: `tiktok`
3. In StreamClip **Settings**, save Client ID + Secret per platform.
4. User connects from **Distribution → Connections**.

### Cloud (managed)

Set client credentials via environment / secrets manager. Users connect without BYO wizard.

## Publish webhooks

Signed JSON POST to global webhook URL and/or per-user webhook (Settings).

| Event | When |
|-------|------|
| `publish.scheduled` | Job created with future `scheduled_at` |
| `publish.published` | Upload succeeded (`external_url` in payload) |
| `publish.failed` | Terminal failure |
| `publish.cancelled` | User cancelled scheduled/pending job |

Header: `X-StreamClip-Signature: sha256=<hmac>` when secret configured.

## Prometheus metrics

| Metric | Labels | Meaning |
|--------|--------|---------|
| `streamclip_publish_jobs_total` | `status`, `platform` | `started`, `succeeded`, `failed`, `cancelled` |
| `streamclip_publish_duration_seconds` | `platform` | Worker wall time (succeeded/failed) |
| `streamclip_vault_saves_total` | `status` | `ready` / `failed` copy tasks |
| `streamclip_vault_quota_denied_total` | — | Saves rejected at tier limit |

Suggested alerts:

- `publish_jobs_total{status="failed"}` > 5/hour
- `publish_duration_seconds` p95 > 120s
- `vault_quota_denied_total` spike (misconfigured tier or abuse)

## Clip Vault retention

- Vault objects live under `vault/{user_id}/{vault_clip_id}/` and are **excluded** from job retention cleanup.
- Tier limits: Free 25, Pro 500 (see `core/billing.py`).
- Deleting a vault clip removes DB row and MinIO keys.

## Troubleshooting

### Publish stuck in `pending`

- Celery worker not running or overloaded.
- Check Redis connectivity.
- Inspect worker logs for `publish_task_failed`.

### Publish fails with `NO_CONNECTION`

- User must connect platform in Distribution.
- Token may be revoked — reconnect.

### Publish fails with `TOKEN_EXPIRED`

- Refresh failed; user must reconnect OAuth.

### Scheduled post did not fire

- Beat not running.
- Check `scheduled_at` is UTC-aware in DB.
- Beat lag: compare `now()` vs `publish_jobs.scheduled_at`.

### `STORAGE_MISSING`

- Source clip or vault copy deleted from MinIO. Re-save to vault or re-render clip.

### TikTok

- Upload uses the Content Posting API **inbox flow** (`video.upload` scope): the
  clip lands in the user's TikTok app inbox and they finish the post there.
- Direct public posting needs the `video.publish` scope + TikTok app audit — not wired.
- Keep `TIKTOK_PUBLISH_ENABLED=false` until your TikTok developer app is approved.

### Webhook not received

- Confirm `STREAMCLIP_WEBHOOKS__ENABLED` or user webhook URL.
- Check outbound network from worker container.
- Verify HMAC secret matches receiver.

### Token key rotation

1. Generate new `TOKEN_ENCRYPTION_KEY`.
2. Re-encrypt `platform_connections` and `install_oauth_apps` (script required — plan for maintenance window).
3. Users may need to reconnect if tokens cannot be decrypted.

## Security checklist

- Never log decrypted OAuth tokens.
- Scope minimization: upload + basic profile only.
- All publish/vault queries scoped by `user_id`.
- Pro gate on mutating distribution endpoints (`require_distribution_access`).

## Related docs

- `COMMERCIAL.md` — licensing and hybrid OAuth planes
- `deploy/PRODUCTION.md` — stack deployment
- `CONTRIBUTING.md` — OpenAPI type regeneration
