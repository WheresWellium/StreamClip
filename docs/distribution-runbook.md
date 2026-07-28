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

`docker-compose.yml` reads `STREAMCLIP_DISTRIBUTION__TOKEN_ENCRYPTION_KEY` and
`STREAMCLIP_DISTRIBUTION__WEB_ORIGIN` from `.env` (see `.env.example`). Generate a
local Fernet key before starting the stack; never commit a real key.
on `api`/`worker`/`gpu-worker` so OAuth connections work out of the box locally — never reuse that key
in production; generate a fresh one per the command above.

```bash

# Platform feature flags
STREAMCLIP_DISTRIBUTION__YOUTUBE_PUBLISH_ENABLED=true
STREAMCLIP_DISTRIBUTION__TIKTOK_PUBLISH_ENABLED=false   # enable when TikTok API approved

# Managed OAuth (Cloud) — optional; BYO uses install_oauth_apps table
STREAMCLIP_DISTRIBUTION__YOUTUBE_CLIENT_ID=
STREAMCLIP_DISTRIBUTION__YOUTUBE_CLIENT_SECRET=
STREAMCLIP_DISTRIBUTION__TIKTOK_CLIENT_KEY=
STREAMCLIP_DISTRIBUTION__TIKTOK_CLIENT_SECRET=

# Global webhooks (optional; users can also set per-account webhook URL)
STREAMCLIP_WEBHOOKS__ENABLED=true
STREAMCLIP_WEBHOOKS__URL=https://hooks.example.com/streamclip
STREAMCLIP_WEBHOOKS__SECRET=<hmac secret>

# Operator alerts (optional; internal support + stack health)
OPS_WEBHOOK_URL=https://hooks.example.com/streamclip-ops
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

**Docker Compose:** the `beat` service in `docker-compose.yml` runs the command above. Confirm with `docker compose ps` (beat Up) or `docker compose logs beat --tail 40`.

**Desktop / in-process:** there is no separate Beat container. With `queue.inprocess_beat`, an internal loop polls due posts every 60s **only while the app is running** (overdue jobs catch up on next launch). See [BETA_KNOWN_ISSUES.md](BETA_KNOWN_ISSUES.md).

### Verify worker / Beat health

- Docker: `docker compose ps` — `worker` and `beat` Up
- `GET /metrics` — check `streamclip_celery_tasks_in_progress`
- Distribution → Queue tab — scheduled jobs should move to pending/publishing within ~60s of `scheduled_at`
- Logs: `publish_completed`, `publish_task_failed`, `publish_webhook_sent`

## Operator alerts and SMTP

`OPS_WEBHOOK_URL` is **separate** from publish webhooks
(`STREAMCLIP_WEBHOOKS__URL` + optional HMAC). Ops alerts are for StreamClip
operators: in-app bug reports, beta feedback, proactive `job_failed`, and Beat
`stack_degraded`. Set on **api**, **worker**, and **beat**.

Canonical contract: [OPS_ALERTING.md (GitHub)](https://github.com/WheresWellium/StreamClip/blob/master/docs/OPS_ALERTING.md) — unsigned JSON POST,
`Content-Type: application/json`, `User-Agent: StreamClip-Ops/1.0`, up to 3
retries, 15s timeout. Prefer Zapier/Make Catch Hook or a custom JSON inbox;
native Discord/Slack hooks need an adapter.

```bash
OPS_WEBHOOK_URL=https://<zapier-make-catch-hook-or-custom-json-inbox>
```

SMTP on **api** + **worker** also covers password-reset and LS license-key
fallback email. Bug reports still persist in `bug_reports` when SMTP is unset.

```bash
SMTP_HOST=smtp.resend.com
SMTP_PORT=587
SMTP_USER=resend
SMTP_PASSWORD=<resend_api_key>
SMTP_FROM=alerts@your-verified-domain.example
SMTP_STARTTLS=true
BUG_REPORT_TO=ops@your-domain.example
```

Resend requires a verified sender domain. Never commit real webhook URLs, Resend
API keys, or operator inboxes. Verify locally with:

```powershell
.\scripts\verify_production_secrets.ps1 -EnvFile .env.production
.\scripts\verify_ops_webhook.ps1 -DryRun
.\scripts\verify_ops_webhook.ps1
```

Full operator checklist: [OPS_ALERTING.md (GitHub)](https://github.com/WheresWellium/StreamClip/blob/master/docs/OPS_ALERTING.md).

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

### OAuth redirect URI checklist

`STREAMCLIP_DISTRIBUTION__WEB_ORIGIN` must equal the browser origin users hit (scheme + host + port, **no** trailing slash). Redirects are built in `core/distribution/credentials.py` as:

```text
{WEB_ORIGIN}/api/distribution/oauth/{platform}/callback
```

Platform ids are **`youtube_shorts`** and **`tiktok`** (not `youtube`).

**Copy-paste — local Docker (default compose):**

| Console field | Exact value |
|---------------|-------------|
| `WEB_ORIGIN` | `http://localhost:3000` |
| Google → Authorized redirect URI | `http://localhost:3000/api/distribution/oauth/youtube_shorts/callback` |
| TikTok → Redirect URI | `http://localhost:3000/api/distribution/oauth/tiktok/callback` |

**Copy-paste — production (replace host):**

| Console field | Exact value |
|---------------|-------------|
| `WEB_ORIGIN` | `https://clip.example.com` |
| Google → Authorized redirect URI | `https://clip.example.com/api/distribution/oauth/youtube_shorts/callback` |
| TikTok → Redirect URI | `https://clip.example.com/api/distribution/oauth/tiktok/callback` |

Operator checklist:

- [ ] Set `STREAMCLIP_DISTRIBUTION__WEB_ORIGIN` on **api** and **worker** (same value)
- [ ] Paste the matching YouTube URI into Google Cloud OAuth client (Authorized redirect URIs)
- [ ] Paste the matching TikTok URI into the TikTok developer app (if enabling TikTok)
- [ ] No trailing slash on `WEB_ORIGIN`; no `/api` prefix on `WEB_ORIGIN` itself
- [ ] Caddy/proxy forwards `/api/*` to the API so the callback hits FastAPI, not Next.js alone
- [ ] After change: reconnect platform in **Distribution → Connections** (old tokens stay valid; new OAuth needs the new URI)

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

### Ops alert not received

- Confirm `OPS_WEBHOOK_URL` is set on api, worker, and beat (not only api).
- Restart env readers: `docker compose up -d api worker beat`.
- Run `.\scripts\verify_ops_webhook.ps1` to isolate container egress from the
  real receiver.
- If pointing at Discord/Slack directly, expect `ops_webhook_bad_status` —
  use a Catch Hook/adapter that accepts StreamClip JSON (no HMAC signature).
- Check logs for `ops_webhook_skipped_unconfigured`, `ops_webhook_failed`, or
  `ops_webhook_bad_status`. See [OPS_ALERTING.md (GitHub)](https://github.com/WheresWellium/StreamClip/blob/master/docs/OPS_ALERTING.md).

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
