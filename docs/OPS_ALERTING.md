# StreamClip — autonomous ops alerting (internal)

**Not published** on the public docs site. Webhook secrets live in env only.

## Purpose

Notify operators **before** testers file bugs — and forward in-app support
forms — without n8n or any middleman workflow tool.

| Source | `event` field |
|--------|----------------|
| `POST /api/support/beta-feedback` | `beta_feedback` |
| `POST /api/support/bug-reports` | `bug_report` |
| Job finished with errors | `job_failed` |
| Beat stack probe (DB/Redis/storage) | `stack_degraded` |
| Celery task crash (when Sentry DSN set) | Sentry issue (not webhook) |

## Operator checklist (do this once)

Secrets stay in **local** `.env` / `.env.production`. Never commit real URLs or API keys.

| Step | Action | Expect |
|------|--------|--------|
| 1 | Stack up: `docker compose up -d api worker beat` | `api` running |
| 2 | Preflight: `.\scripts\verify_ops_webhook.ps1 -DryRun` | `READY` (or clear SKIP + fix) |
| 3 | Mock path: `.\scripts\verify_ops_webhook.ps1` | `PASS: OPS webhook path verified` |
| 4 | Create Catch Hook / JSON inbox (see receivers below) | operator-owned URL |
| 5 | Paste real `OPS_WEBHOOK_URL` into **local** `.env` / `.env.production` | never commit the real URL |
| 6 | Optional Resend SMTP (section below) + `BUG_REPORT_TO` | verified sending domain |
| 7 | Optional `STREAMCLIP_OBSERVABILITY__SENTRY_DSN` | API + worker crashes in Sentry |
| 8 | Restart env readers | `docker compose up -d api worker beat` |
| 9 | Live check: Help (?) → **Beta feedback** | receiver JSON; API `ops_notification: "queued"` |

Help / dry-run (no stack required for `-Help`; `-DryRun` tolerates down stack):

```powershell
.\scripts\verify_ops_webhook.ps1 -Help
.\scripts\verify_ops_webhook.ps1 -DryRun
```

Mock verify injects a temporary URL into the `api` container — **local
`OPS_WEBHOOK_URL` may be unset**. Exit `2` = SKIP (toolchain/stack missing),
not a broken webhook path.

Production secrets lint (warns if webhook/Sentry/Resend incomplete):

```powershell
.\scripts\verify_production_secrets.ps1 -EnvFile .env.production
```

## Environment

Set on **api**, **worker**, and **beat**. Support forms queue from the API to the
worker; stack probes run from Beat.

```bash
OPS_WEBHOOK_URL=https://<your-endpoint>/hooks/streamclip-ops
```

Optional SMTP (Docker self-host only) for bug-report email:

```bash
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=streamclip@example.com
SMTP_STARTTLS=true
BUG_REPORT_TO=ops@example.com
```

### Resend SMTP (same code path)

1. In Resend: verify the sending domain.
2. Create an API key; use it only as `SMTP_PASSWORD` (never commit).
3. Set on **api** and **worker**:

```bash
SMTP_HOST=smtp.resend.com
SMTP_PORT=587
SMTP_USER=resend
SMTP_PASSWORD=<resend_api_key>
SMTP_FROM=alerts@your-verified-domain.example
SMTP_STARTTLS=true
BUG_REPORT_TO=ops@your-domain.example
```

Optional Sentry (API + workers):

```bash
STREAMCLIP_OBSERVABILITY__SENTRY_DSN=https://...@o....ingest.sentry.io/...
```

### Legacy env alias (do not set new installs)

`core/notify/ops_webhook.py` still reads **`N8N_OPS_WEBHOOK_URL`** if
`OPS_WEBHOOK_URL` is empty (one-release compat). Prefer `OPS_WEBHOOK_URL` only.
Do not reintroduce n8n workflows. Cleanup of the alias is tracked as GAP **O13**.

## Receiver options (pick one)

StreamClip POSTs **unsigned** JSON (`Content-Type: application/json`,
`User-Agent: StreamClip-Ops/1.0`). The URL is the secret — there is no HMAC.

| Receiver | How |
|----------|-----|
| **Zapier / Make Catch Hook** | **Preferred.** Create a Catch Hook; map fields → Outlook/Teams/Discord/Slack; paste URL into `OPS_WEBHOOK_URL` |
| **Custom agent inbox** | Any HTTPS endpoint that accepts arbitrary JSON POSTs |
| **Native Discord / Slack incoming webhook** | **Not drop-in.** Those platforms reject StreamClip-shaped JSON — put an adapter in front that maps to `content` / `text` |
| **SMTP only** | Leave `OPS_WEBHOOK_URL` unset; set `SMTP_*` + `BUG_REPORT_TO` |

## Sample payloads

### Support form

```json
{
  "event": "bug_report",
  "id": "abc123",
  "severity": "high",
  "categories": ["ingest"],
  "message": "First job stuck on transcribe",
  "user_id": null,
  "device_id": "a1b2c3…",
  "job_id": "job_…",
  "environment": { "page": "/jobs/…" },
  "created_at": "2026-07-08T12:00:00+00:00",
  "app": "streamclip"
}
```

### Proactive job failure

```json
{
  "event": "job_failed",
  "job_id": "job_…",
  "done_count": 2,
  "error_count": 1,
  "status": "error",
  "app": "streamclip"
}
```

### Stack degraded (Beat every 5 min; 15 min cooldown)

```json
{
  "event": "stack_degraded",
  "status": "degraded",
  "checks": {"database": false, "redis": true, "storage": true},
  "failures": ["database: …"],
  "app": "streamclip"
}
```

Requires Beat (Docker `beat` service) or desktop `queue.inprocess_beat`. Task:
`core.tasks.notify_tasks.probe_stack_health_ops_alert`.

## Extended verification

After checklist step 9:

1. Force a failing job (or mock) and confirm `job_failed` arrives.
2. Optional: stop Postgres briefly and wait ≤5 min for `stack_degraded` (or run
   the task once via Flower/celery call).
3. Log greps (worker): `ops_webhook_sent`, `ops_webhook_failed`,
   `ops_webhook_skipped_unconfigured`, `ops_webhook_bad_status`.

## Privacy

- Never commit `OPS_WEBHOOK_URL` or inbox addresses to public docs
- Payloads exclude video URLs and clip content by design
- Desktop builds: bake `OPS_WEBHOOK_URL` at operator build time if you want
  creator installs to forward support forms without local SMTP

## Sentry (autonomous triage)

With `STREAMCLIP_OBSERVABILITY__SENTRY_DSN` set:

- API process captures unhandled FastAPI/SQLAlchemy errors
- Celery workers capture task failures
- Use Sentry MCP / Seer in Cursor to query and triage issues without waiting
  for a tester report

Recommended Sentry alert rules (configure in Sentry UI, not this repo):

- New issue → Slack/email
- Error rate spike on `streamclip` project
- Regression of a resolved issue
