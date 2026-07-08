# StreamClip — n8n ops routing (internal)

**Not published** on the public docs site. Studio inbox and webhook secrets live here only.

## Purpose

Route in-app **Beta feedback** and **Report a bug** submissions to the Pogi Studios
Outlook inbox via n8n — without exposing the address in the app, repo, or public docs.

| App endpoint | n8n `event` field |
|--------------|-------------------|
| `POST /api/support/beta-feedback` | `beta_feedback` |
| `POST /api/support/bug-reports` | `bug_report` |

## Environment (StreamClip stack)

Set on **api** and **worker** (worker sends the webhook task):

```bash
N8N_OPS_WEBHOOK_URL=https://<your-n8n-host>/webhook/<secret-path>
```

Optional legacy SMTP path (Docker self-host only) — not used for desktop `.exe`:

```bash
SMTP_HOST=...
BUG_REPORT_TO=...
```

## n8n workflow (recommended)

1. **Webhook** node — POST, path e.g. `streamclip-ops`
2. **Switch** on `{{ $json.body.event }}`
   - `beta_feedback` → subject prefix `[StreamClip Beta]`
   - `bug_report` → subject prefix `[StreamClip Bug]`
3. **Microsoft Outlook** node — send email to studio inbox (configure in n8n UI only)
4. Optional **Set** node to format HTML body from payload fields:
   - `message`, `severity`, `categories`, `user_id`, `device_id`, `job_id`, `environment`

### Sample webhook payload

```json
{
  "event": "beta_feedback",
  "id": "abc123",
  "severity": "low",
  "categories": ["ui"],
  "message": "First job stuck on transcribe",
  "user_id": null,
  "device_id": "a1b2c3…",
  "job_id": null,
  "environment": { "kind": "beta_feedback", "topic": "help", "page": "/jobs/…" },
  "created_at": "2026-07-08T12:00:00+00:00",
  "app": "streamclip"
}
```

## Hosting n8n

You previously connected n8n to v0/Vercel and a Shopify custom app. For StreamClip:

| Option | Notes |
|--------|-------|
| **Vultr VPS** | Always-on, same pattern as Shopify glue; ~$6–12/mo for small box |
| **n8n Cloud** | Fastest if you already have a seat |
| **Local tunnel** | Dev only — not for beta |

After deploy, paste the production webhook URL into `.env` / Vultr secrets.

## Verification

1. Set `N8N_OPS_WEBHOOK_URL` and restart `api` + `worker`
2. In the app header: **Beta feedback** (top) → send test message
3. Confirm Outlook receives mail; check n8n execution log
4. Repeat with **Report a bug**

## Privacy

- Never commit `N8N_OPS_WEBHOOK_URL` or inbox address to public docs
- Payloads exclude video URLs and clip content by design
- Desktop installs store rows locally **and** forward to n8n when URL is set at build/deploy time

## macOS

Same webhook URL and n8n workflow — no changes when the `.dmg` ships; tag `platform`
in Sentry separately (future).
