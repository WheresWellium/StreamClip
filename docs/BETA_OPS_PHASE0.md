# Phase 0 operator runbook (no n8n required)

**Audience:** StreamClip operators during Docker / creator beta.  
**When n8n is live:** add `N8N_OPS_WEBHOOK_URL` and follow [OPS_N8N_SETUP.md](OPS_N8N_SETUP.md).

---

## 1. What works without n8n

| Channel | Stored | Email alert | n8n alert |
|---------|--------|-------------|-----------|
| Report a bug | `bug_reports` table | Only if `SMTP_*` + `BUG_REPORT_TO` set | Only if `N8N_OPS_WEBHOOK_URL` set |
| Beta feedback | Same table (`environment.kind=beta_feedback`) | No | Optional webhook |

Reports always persist locally first. Poll the database or admin API until webhooks are configured.

---

## 2. Issue beta keys

Generate keys for the cohort (status `issued` — testers paste in **Settings → License**):

```powershell
docker compose exec api python scripts/issue_beta_keys.py --csv cohort.csv
# or
docker compose exec api python scripts/issue_beta_keys.py --emails tester1@example.com,tester2@example.com
```

**Max access** (distribution + admin API + highest quotas — for power testers / your own account):

```powershell
docker compose exec api python scripts/issue_beta_keys.py --emails you@example.com --tier admin
```

Output CSV: `email,license_key,order_id,tier`. **Do not commit this file.** Send keys via your invite email or future n8n workflow.

Dry run (no DB writes):

```powershell
docker compose exec api python scripts/issue_beta_keys.py --emails you@example.com --tier admin --dry-run
```

Local dev shortcut (auto-activates on `streamclip-local-dev`, upgrades all DB users to admin):

```powershell
docker compose exec api python scripts/grant_dev_pro.py
# single user:
docker compose exec -e DEV_GRANT_EMAIL=you@example.com api python scripts/grant_dev_pro.py
```

Web testers bind keys to their browser device id (shown in Settings → License after activation attempt).

---

## 3. Read support reports

**CLI (JSON lines):**

```powershell
docker compose exec api python scripts/list_support_reports.py --limit 20
docker compose exec api python scripts/list_support_reports.py --kind feedback
docker compose exec api python scripts/list_support_reports.py --kind bug
```

**Admin API** (requires admin JWT):

```http
GET /api/admin/bug-reports?limit=50
Authorization: Bearer <admin_token>
```

**SQL:**

```sql
SELECT id, severity, categories, message, user_id, device_id, created_at, environment
FROM bug_reports
ORDER BY created_at DESC
LIMIT 50;
```

Beta feedback rows have `environment->>'kind' = 'beta_feedback'`.

---

## 4. Invite email template (manual send)

Subject: **StreamClip Phase 0 beta — your access**

Body (replace placeholders):

```
Hi {name},

You're invited to the StreamClip Phase 0 beta.

Install: https://streamclip.vercel.app/BETA_DOWNLOAD/
Quickstart: https://streamclip.vercel.app/BETA_TESTER_QUICKSTART/

Pro license key (Settings → License):
{license_key}

Use "Beta feedback" or "Report a bug" in the app header for support.
We read every submission even if you don't get an auto-reply yet.

Thanks,
Wellium
```

---

## 5. Optional env (when ready)

Add to `.env` / production secrets — all optional for Phase 0:

| Variable | Purpose |
|----------|---------|
| `BUG_REPORT_TO` | SMTP destination for bug reports |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Outbound mail |
| `N8N_OPS_WEBHOOK_URL` | Forward bug + feedback payloads to n8n → Outlook |
| `SENTRY_DSN` | Error telemetry |

See `.env.example` and [OPS_N8N_SETUP.md](OPS_N8N_SETUP.md).

---

## 6. Pre-invite checklist

- [ ] `verify_stack.ps1` green on operator machine
- [ ] GitHub Release / installer linked from [BETA_DOWNLOAD.md](BETA_DOWNLOAD.md)
- [ ] Keys issued via `issue_beta_keys.py`; CSV stored securely (not in git)
- [ ] At least one admin account exists for `GET /api/admin/bug-reports`
- [ ] [BETA_KNOWN_ISSUES.md](BETA_KNOWN_ISSUES.md) current for this wave
