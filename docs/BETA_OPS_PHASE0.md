# Phase 0 operator runbook

**Audience:** qClip operators during Docker / creator beta.  
**Ops alerts:** set `OPS_WEBHOOK_URL` and follow [OPS_ALERTING.md](OPS_ALERTING.md).
**Observability:** health, `/metrics`, log-tail, and opt-in tester bundles live in [BETA_OBSERVABILITY.md](BETA_OBSERVABILITY.md).

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

Subject: **qClip Phase 0 beta — your access**

Body (replace placeholders):

```
Hi {name},

You're in — welcome to the qClip Phase 0 beta.

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

Add to `.env` / production secrets — all optional for Phase 0, but
`OPS_WEBHOOK_URL` is recommended before adding more testers.

Full delivery contract (headers, **no HMAC**, payloads, Resend path):
[OPS_ALERTING.md](OPS_ALERTING.md).

| Variable | Purpose |
|----------|---------|
| `BUG_REPORT_TO` | SMTP destination for bug reports only |
| `SMTP_HOST` … `SMTP_FROM`, `SMTP_STARTTLS` | Outbound mail (bug reports, password reset, LS license fallback) |
| `OPS_WEBHOOK_URL` | Unsigned JSON POST for bug + feedback + `job_failed` + `stack_degraded` |
| `STREAMCLIP_OBSERVABILITY__SENTRY_DSN` | Error telemetry (API + workers) |

Fast path (full checklist: [OPS_ALERTING.md](OPS_ALERTING.md)):

1. Stack up: `docker compose up -d api worker beat`.
2. Mock egress (no real URL; does not write `.env`):

   ```powershell
   .\scripts\verify_ops_webhook.ps1 -DryRun
   .\scripts\verify_ops_webhook.ps1
   ```

   Expect `PASS` (or exit `2` SKIP if python/docker/`api` missing — not a webhook bug).
3. Create a **Zapier/Make Catch Hook** or custom HTTPS JSON inbox (preferred).
   Native Discord/Slack incoming webhooks reject qClip-shaped JSON — use
   an adapter that maps fields to `content` / `text`.
4. Put the secret URL in **local** `.env` / `.env.production` as `OPS_WEBHOOK_URL`
   (operator action — do not invent URLs in docs/commits). Prefer
   `OPS_WEBHOOK_URL`; legacy `N8N_OPS_WEBHOOK_URL` still read if primary empty (GAP O13).
5. If using Resend for email, verify the sender domain and set:

   ```bash
   SMTP_HOST=smtp.resend.com
   SMTP_PORT=587
   SMTP_USER=resend
   SMTP_PASSWORD=<resend_api_key>
   SMTP_FROM=alerts@your-verified-domain.example
   SMTP_STARTTLS=true
   BUG_REPORT_TO=ops@your-domain.example
   ```

6. Restart env readers: `docker compose up -d api worker beat`
   (production: `docker compose -f docker-compose.prod.yml --env-file .env.production up -d api worker beat`).
7. Submit one in-app **Beta feedback** and confirm the real receiver gets JSON
   with `User-Agent: qClip-Ops/1.0`. Expect API `ops_notification: "queued"`.

See `.env.example`, `.env.production.example`, and [OPS_ALERTING.md](OPS_ALERTING.md).

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

### LS purchase-to-activate evidence (leave unchecked until run)

Use this for MASTER §8.19 / Phase 0 exit evidence. This is an operator checklist, not a claim that the purchase has happened.

1. In Lemon Squeezy, open the beta product / variant used by `STREAMCLIP_COMMERCE__LEMON_SQUEEZY_BETA_VARIANT_ID`.
   - [ ] Confirm the checkout is the intended beta / Pro SKU (`Lead Magnet` or one-time purchase, not subscription).
   - [ ] Confirm license keys are enabled and the receipt/download page includes the beta kit plus `qClip-Setup-win-x64.exe`.
   - [ ] Open the webhook configuration and confirm the URL is `{API_ORIGIN}/api/commerce/webhooks/lemon-squeezy`.
2. In the operator shell, run the env preflight:

   ```powershell
   .\scripts\verify_ls_beta_config.ps1
   ```

   - [ ] Success looks like all required `STREAMCLIP_COMMERCE__LEMON_SQUEEZY_*` vars `OK` and the checkout URL responding or redirecting.
3. Copy the checkout URL from Lemon Squeezy and complete one staging/test checkout with a non-production buyer email.
   - [ ] Success in Lemon Squeezy: an order exists for that buyer and either `license_key_created` delivered a key or `order_created` triggered the qClip fallback email.
   - [ ] Success in webhook delivery: the Lemon Squeezy webhook attempt returns HTTP 2xx.
4. Confirm the key reached qClip:

   ```powershell
   docker compose exec postgres psql -U streamclip -d streamclip -c "select order_id, customer_email, tier, status, activation_count, created_at from install_licenses order by created_at desc limit 5;"
   ```

   - [ ] Success before activation: the test buyer row is present with `status='issued'`, `tier='admin'` or `tier='pro'`, and `activation_count=0`.
5. Activate the delivered key from a clean browser / VM:
   - [ ] Log in, open **Settings → License**, paste the delivered key, and click **Activate**.
   - [ ] Success in the UI: the license panel shows the upgraded tier and no paywall blocks Pro/Admin features.
   - [ ] Success in the DB: the same license row changes to `status='activated'` with `activation_count >= 1`.

Do not commit secrets or real product/variant IDs.

---

## 7. Pre-invite checklist

Full operator pack: [BETA_INVITE_PACK.md](BETA_INVITE_PACK.md).

**Local Docker stack (operator host):**

- `.\scripts\start.ps1` — Phase 0 alias/wrapper for `start_local.ps1` (compose up, migrations, then full verify)
- `.\scripts\health.ps1` — fast second-terminal smoke (no pytest)
- `.\scripts\verify_stack.ps1` — full gate (keep this as invite clearance)

- [ ] `verify_stack.ps1` green on operator machine
- [ ] Zip + `.exe` on LS product files (or checkout link in invite email — not GitHub; repo may be private)
- [ ] Keys issued via `issue_beta_keys.py`; CSV stored securely (not in git)
- [ ] At least one admin account exists for `GET /api/admin/bug-reports`
- [ ] [BETA_KNOWN_ISSUES.md](BETA_KNOWN_ISSUES.md) current for this wave
- [ ] Feedback channel live: in-app reports + GitHub **Beta bug report** template (or Discord `#beta-bugs`)
- [ ] OAuth redirect URIs match `WEB_ORIGIN` — copy-paste checklist in [distribution-runbook.md](distribution-runbook.md#oauth-redirect-uri-checklist)
- [ ] On-call roles filled in [BETA_ON_CALL.md](BETA_ON_CALL.md) (TBD → real contacts)
- [ ] `OPS_WEBHOOK_URL` (+ optional Sentry DSN) set; api/worker/beat restarted; `.\scripts\verify_ops_webhook.ps1` passed — [OPS_ALERTING.md](OPS_ALERTING.md)
- [ ] Beta observability terminal ready: health checks + log tail, or optional Prometheus scrape — [BETA_OBSERVABILITY.md](BETA_OBSERVABILITY.md)
- [ ] Scheduled publish: Beat documented — [distribution-runbook.md](distribution-runbook.md#celery-worker-and-beat) (Docker `beat` service; desktop in-process note + [BETA_KNOWN_ISSUES](BETA_KNOWN_ISSUES.md))
- [ ] LS dashboard product config checked (§6) if testing paid purchase → activate
- [ ] Fresh-reader quickstart walk recorded ([BETA_INVITE_PACK](BETA_INVITE_PACK.md) §2)
