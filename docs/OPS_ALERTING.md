# qClip — autonomous ops alerting (internal)

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

## Environment

Set on **api** and **worker**:

```bash
OPS_WEBHOOK_URL=https://<your-endpoint>/hooks/streamclip-ops
```

Optional SMTP (Docker self-host only) for bug-report email:

```bash
SMTP_HOST=...
BUG_REPORT_TO=...
```

Optional Sentry (API + workers):

```bash
STREAMCLIP_OBSERVABILITY__SENTRY_DSN=https://...@o....ingest.sentry.io/...
```

## Receiver options (pick one)

| Receiver | How |
|----------|-----|
| **Discord / Slack** | Paste the platform's incoming webhook URL into `OPS_WEBHOOK_URL` |
| **Zapier Catch Hook** | Create a Catch Hook; map fields → Outlook/Teams; paste URL |
| **Custom agent inbox** | Any HTTPS POST JSON endpoint your autonomous agent owns |
| **SMTP only** | Leave `OPS_WEBHOOK_URL` unset; set `SMTP_*` + `BUG_REPORT_TO` |

There is **no n8n dependency**. Do not reintroduce `N8N_OPS_WEBHOOK_URL`
except as a temporary alias (still read for one release).

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

## Verification

1. Set `OPS_WEBHOOK_URL` (and optionally `STREAMCLIP_OBSERVABILITY__SENTRY_DSN`) in `.env` / `.env.production`
2. Restart `api` + `worker` + `beat` (`docker compose up -d api worker beat`)
3. Open **Help menu (?)** → **Beta feedback** or **Report a bug**
4. Confirm the receiver got the JSON
5. Force a failing job (or mock) and confirm `job_failed` arrives
6. Optional: stop Postgres briefly and wait ≤5 min for `stack_degraded` (or run the task once via Flower/celery call)

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
