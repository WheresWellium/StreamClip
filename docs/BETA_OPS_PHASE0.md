# Phase 0 operator runbook

**Audience:** StreamClip operators during Docker / creator beta.  
**Ops alerts:** set `OPS_WEBHOOK_URL` and follow [OPS_ALERTING.md](OPS_ALERTING.md).

---

## 1. Support channels

| Channel | Stored | Email alert | Ops webhook |
|---------|--------|-------------|-------------|
| Report a bug | `bug_reports` table | Only if `SMTP_*` + `BUG_REPORT_TO` set | Only if `OPS_WEBHOOK_URL` set |
| Beta feedback | Same table (`environment.kind=beta_feedback`) | No | Optional webhook |
| Job finished with errors | Prometheus + optional webhook | No | `event=job_failed` |
| GitHub Issues (beta template) | Public issue | — | — |

Reports always persist locally first. Poll the database or admin API until webhooks are configured.

### Feedback channel (Phase 0 — no Discord required)

**Primary (in-app):** testers use **Report a bug** / **Beta feedback** in the app header → rows in `bug_reports` (see §3).

**Public fallback:** GitHub issue template [`.github/ISSUE_TEMPLATE/beta-bug.yml`](../.github/ISSUE_TEMPLATE/beta-bug.yml) — requires **job id**, GPU/compute, OS, steps, expected vs actual, optional logs. Labels: `beta`, `bug`.

Operator pin (invite email or Discussions if enabled):

> File beta bugs with the **Beta bug report** template. Include job id + `docker compose logs worker --tail 80` (redact secrets). Check [BETA_KNOWN_ISSUES.md](BETA_KNOWN_ISSUES.md) first.

Optional later: Discord `#beta-bugs` mirroring the same fields; not required to open Phase 0.

---

## 2. Issue beta keys

Generate keys for the cohort (status `issued` — testers paste in **Settings → License**).

**Default is now `admin` tier** — all beta keys unlock full access (distribution + admin API + highest quotas). No `--tier` flag needed:

```powershell
docker compose exec -e PYTHONPATH=/app api python scripts/issue_beta_keys.py --csv cohort.csv
# or
docker compose exec -e PYTHONPATH=/app api python scripts/issue_beta_keys.py --emails tester1@example.com,tester2@example.com
```

Explicit admin (same as default — kept for clarity in automated scripts):

```powershell
docker compose exec -e PYTHONPATH=/app api python scripts/issue_beta_keys.py --emails you@example.com --tier admin
```

Output CSV: `email,license_key,order_id,tier`. **Do not commit this file.** Send keys via your invite email.

Dry run (no DB writes):

```powershell
docker compose exec -e PYTHONPATH=/app api python scripts/issue_beta_keys.py --emails you@example.com --tier admin --dry-run
```

One-command admin key for local testing (prints a ready-to-paste `SCPRO-…` admin key):

```powershell
.\scripts\dev_admin_key.ps1                 # Windows (default dev@streamclip.local)
./scripts/dev_admin_key.sh you@example.com  # macOS / Linux
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

## 4. Invite email template (attach the beta .zip — repo is private)

**The repo is private** (Option B, decided 2026-07-09) — there is no public GitHub
Releases link testers can use. The `.zip` built by `scripts/build_beta_zip.py`
**must be attached directly to the invite email**. Do not link to GitHub anywhere
in tester-facing copy.

```powershell
python scripts/build_beta_zip.py    # writes dist/StreamClip-beta.zip (~1 MB)
python scripts/send_beta_test_info_emails.py --csv cohort.csv --keys-csv <keys.csv> `
    --env-file .env.beta-mail --send
```

Copy `.env.beta-mail.example` → `.env.beta-mail` (gitignored) and set `SMTP_PASSWORD`
for the `wheres@wellium.work` Microsoft 365 mailbox before `--send`.

| Variable | Outlook / M365 value |
|----------|----------------------|
| `SMTP_HOST` | `smtp.office365.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | `wheres@wellium.work` |
| `SMTP_FROM` | `wheres@wellium.work` |
| `SMTP_PASSWORD` | Mailbox or app password (not in git) |
| `SMTP_STARTTLS` | `true` |

Ensure **SMTP AUTH** is enabled for the mailbox (M365 admin → user → Mail →
Manage email apps → Authenticated SMTP). The script attaches
`dist/StreamClip-beta.zip` (~0.7 MB) to every message.

The sender script (`scripts/send_beta_test_info_emails.py`) already attaches
`dist/StreamClip-beta.zip` and uses this subject/body. For a fully manual send,
replicate it exactly — same attachment, same subject:

Subject: **BETA TEST INFO**

Body (replace placeholders):

```
Hi {name},

You're in — welcome to the StreamClip Phase 0 beta.

Getting started (no GitHub account needed):

1. The StreamClip beta files are attached to this email as a .zip.
   Extract it to any folder (e.g. C:\StreamClip or ~/StreamClip).

2. Quickstart — install to your first clip (~15 min):
   https://streamclip-henna.vercel.app/BETA_TESTER_QUICKSTART/

3. Paste your license key in Settings → License after logging in:
   {license_key}

This key gives you full access to every feature. No feature gates.

The short path:
- Install Docker Desktop (free) and keep it running
- Extract the attached .zip to any folder
- Run the one start command from the quickstart
- Open http://localhost:3000
- Paste a public video link and wait for clips

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
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Outbound mail (Docker bug reports + operator beta sends via `.env.beta-mail`) |
| `OPS_WEBHOOK_URL` | Forward bug + feedback + `job_failed` to Discord/Slack/agent inbox |
| `STREAMCLIP_OBSERVABILITY__SENTRY_DSN` | Error telemetry (API + workers) |

See `.env.example` and [OPS_ALERTING.md](OPS_ALERTING.md).

---

## 6. Lemon Squeezy product config (dashboard — not in repo)

Operator checklist before relying on paid Pro keys (see [COMMERCIAL.md](../COMMERCIAL.md), `.env.example` / `.env.production.example`):

- [ ] Product is a **one-time purchase** (not a subscription) — matches perpetual entitlement in `COMMERCIAL.md`
- [ ] Webhook URL points at the live API: `{API_ORIGIN}/api/commerce/webhooks/lemon-squeezy` (events that deliver license keys)
- [ ] `STREAMCLIP_COMMERCE__LEMON_SQUEEZY_WEBHOOK_SECRET` / `LEMON_SQUEEZY_WEBHOOK_SECRET` matches the signing secret shown in the LS dashboard
- [ ] `STREAMCLIP_COMMERCE__LEMON_SQUEEZY_API_KEY` / `LEMON_SQUEEZY_API_KEY` set if API calls are needed
- [ ] If audio-ingest unlock is sold: `STREAMCLIP_COMMERCE__AUDIO_INGEST_VARIANT_IDS` lists the LS **variant** IDs from the dashboard (comma-separated; see `.env.production.example`)

Do not commit secrets or real product/variant IDs.

---

## 7. Pre-invite checklist

Full operator pack: [BETA_INVITE_PACK.md](BETA_INVITE_PACK.md).

- [ ] `verify_stack.ps1` green on operator machine
- [ ] Beta `.zip` built (`python scripts/build_beta_zip.py`) — testers get code via email attachment only
- [ ] Keys issued via `issue_beta_keys.py`; CSV stored securely (not in git)
- [ ] At least one admin account exists for `GET /api/admin/bug-reports`
- [ ] [BETA_KNOWN_ISSUES.md](BETA_KNOWN_ISSUES.md) current for this wave
- [ ] Feedback channel live: in-app reports + GitHub **Beta bug report** template (or Discord `#beta-bugs`)
- [ ] OAuth redirect URIs match `WEB_ORIGIN` — copy-paste checklist in [distribution-runbook.md](distribution-runbook.md#oauth-redirect-uri-checklist)
- [ ] On-call roles filled in [BETA_ON_CALL.md](BETA_ON_CALL.md) (TBD → real contacts)
- [ ] `OPS_WEBHOOK_URL` (+ optional Sentry DSN) set; api/worker/beat restarted — [OPS_ALERTING.md](OPS_ALERTING.md)
- [ ] Scheduled publish: Beat documented — [distribution-runbook.md](distribution-runbook.md#celery-worker-and-beat) (Docker `beat` service; desktop in-process note + [BETA_KNOWN_ISSUES](BETA_KNOWN_ISSUES.md))
- [ ] LS dashboard product config checked (§6) if testing paid purchase → activate
- [ ] Fresh-reader quickstart walk recorded ([BETA_INVITE_PACK](BETA_INVITE_PACK.md) §2)
