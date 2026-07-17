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

**Primary (in-app):** testers open the **Help menu (?)** → **Report a bug** / **Beta feedback** → rows in `bug_reports` (see §3).

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

You're in — welcome to the StreamClip Phase 0 beta.

Get started (no GitHub account needed):
https://streamclip-henna.vercel.app/BETA_DOWNLOAD/

Quickstart guide (step-by-step, ~15 min):
https://streamclip-henna.vercel.app/BETA_TESTER_QUICKSTART/

Your license key — paste in Settings → License after logging in:
{license_key}

This key gives you full access to every feature. No feature gates.

Open the **Help menu (?)** in the app header → **Beta feedback** or **Report a bug** for support.
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
| `OPS_WEBHOOK_URL` | Forward bug + feedback + `job_failed` to Discord/Slack/agent inbox |
| `STREAMCLIP_OBSERVABILITY__SENTRY_DSN` | Error telemetry (API + workers) |

See `.env.example` and [OPS_ALERTING.md](OPS_ALERTING.md).

---

## 6. Lemon Squeezy product config (dashboard — not in repo)

Operator checklist before relying on paid Pro keys (see [COMMERCIAL.md](../COMMERCIAL.md), `.env.example` / `.env.production.example`):

- [ ] Product is a **one-time purchase** (not a subscription) — matches perpetual entitlement in `COMMERCIAL.md`
- [ ] **Beta Lead Magnet** variant ID in `STREAMCLIP_COMMERCE__LEMON_SQUEEZY_BETA_VARIANT_ID` (maps to ADMIN tier)
- [ ] **Checkout URL** in `STREAMCLIP_COMMERCE__LEMON_SQUEEZY_CHECKOUT_URL` for invite emails
- [ ] Zip + `.exe` uploaded to LS product files (not GitHub — repo may be private)
- [ ] `.\scripts\verify_ls_beta_config.ps1` passes before invites — see [BETA_DISTRIBUTION.md](BETA_DISTRIBUTION.md)
- [ ] Webhook URL points at the live API: `{API_ORIGIN}/api/commerce/webhooks/lemon-squeezy` (events that deliver license keys)
- [ ] `STREAMCLIP_COMMERCE__LEMON_SQUEEZY_WEBHOOK_SECRET` / `LEMON_SQUEEZY_WEBHOOK_SECRET` matches the signing secret shown in the LS dashboard
- [ ] `STREAMCLIP_COMMERCE__LEMON_SQUEEZY_API_KEY` / `LEMON_SQUEEZY_API_KEY` set if API calls are needed
- [ ] If audio-ingest unlock is sold: `STREAMCLIP_COMMERCE__AUDIO_INGEST_VARIANT_IDS` lists the LS **variant** IDs from the dashboard (comma-separated; see `.env.production.example`)

Do not commit secrets or real product/variant IDs.

---

## 7. Pre-invite checklist

Full operator pack: [BETA_INVITE_PACK.md](BETA_INVITE_PACK.md).

- [ ] `verify_stack.ps1` green on operator machine
- [ ] Zip + `.exe` on LS product files (or checkout link in invite email — not GitHub; repo may be private)
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
