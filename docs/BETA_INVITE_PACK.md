# Phase 0 invite pack — operator checklist (§8.14–8.15)

**Audience:** Operator sending the first Docker technical cohort.  
**Do not commit** real emails, license keys, or webhook URLs.

---

## 1. Before you send (binary)

| Gate | Done? | Where |
|------|-------|-------|
| Coverage ≥95% + clean-slate stack | **YES** (2026-07-09) | `BETA_GO_LIVE` §1 / §8 |
| Feedback channel (in-app + GitHub template) | **YES** | §8.11 |
| On-call runbook | **YES** (fill TBD names) | `BETA_ON_CALL.md` §1 |
| OAuth redirect URIs | **YES** (checklist) | `distribution-runbook.md` |
| Beat / scheduled publish docs | **YES** | `distribution-runbook` + quickstart |
| `OPS_WEBHOOK_URL` set on api+worker+beat | ☐ you | `.env` / `.env.production` |
| Optional `STREAMCLIP_OBSERVABILITY__SENTRY_DSN` | ☐ you | same |
| On-call TBD → real contacts | ☐ you | `BETA_ON_CALL.md` |
| Cohort CSV + keys issued | **YES** (2026-07-09, 5 testers regen) | below + `dist/phase0-invite-pack/` |
| Fresh-reader walk of quickstart | **YES** (2026-07-09) | §2 below |

---

## 2. Fresh-reader review (§8.14) — 20 min

Hand someone who has **never** run this repo:

1. Open [BETA_TESTER_QUICKSTART](https://streamclip-henna.vercel.app/BETA_TESTER_QUICKSTART/)
2. Follow Steps 1–4 only (Docker up → `verify_stack.ps1`)
3. Capture: stuck step, missing link, wrong path, unclear GPU note

Operator records result here (private notes OK):

| Date | Reviewer | Stuck at step? | Fixes filed? |
|------|----------|----------------|--------------|
| 2026-07-09 | Agent fresh-reader walk (operator host) | No P0 blockers | Yes — `SCBETA`→`SCPRO` key format; `start_local.ps1` stale “exe not built”; Step 4 “beta channel” → in-app Report a bug |

**Walk evidence:** `verify_stack.ps1` EXIT 0 (health + full unit suite); published quickstart/download HTTP 200; linked paths (`start_local`, tutorials, known issues) present. MASTER §8.14 ✅.

---

## 3. Issue keys (§8.15)

```powershell
# cohort.csv columns: email[,name]  — do not commit (see cohort.example.csv)
Copy-Item cohort.example.csv cohort.csv   # then edit real emails
New-Item -ItemType Directory -Force -Path dist\phase0-invite-pack | Out-Null
docker compose exec -e PYTHONPATH=/app -T api python scripts/issue_beta_keys.py --csv cohort.csv `
  | Select-Object -SkipLast 0 | Out-File -Encoding utf8 dist\phase0-invite-pack\keys.csv
# Prefer capturing only CSV lines; strip docker log noise if present.

# Build ready-to-paste invite emails (does not send):
.\scripts\prepare_invite_pack.ps1 -KeysCsv dist\phase0-invite-pack\keys.csv
```

Output: `email,license_key,order_id,tier`. Store in password manager. Default tier is `admin`.
Pack output (gitignored): `dist/phase0-invite-pack/emails/*.txt` + `SEND_CHECKLIST.txt`.

Dry run (no DB writes):

```powershell
docker compose exec -e PYTHONPATH=/app api python scripts/issue_beta_keys.py --emails you@example.com --dry-run
```

---

## 4. Ops webhook + Sentry (real envs)

**Path check (no secrets):** with the Docker stack up, run:

```powershell
.\scripts\verify_ops_webhook.ps1
```

Expect `PASS: OPS webhook path verified`. This uses a temporary local mock on
`host.docker.internal` — it does **not** write to `.env`.

Then paste real values into **local** `.env` and **prod** `.env.production` (never git):

```bash
OPS_WEBHOOK_URL=https://<discord-or-slack-or-agent-inbox>
STREAMCLIP_OBSERVABILITY__SENTRY_DSN=https://...@o....ingest.sentry.io/...
```

Then:

```powershell
docker compose up -d api worker beat
# prod:
# docker compose -f docker-compose.prod.yml --env-file .env.production up -d
.\scripts\verify_production_secrets.ps1   # warns if webhook/Sentry missing
```

Verify live: submit in-app **Beta feedback** → receiver gets `event=beta_feedback`.  
Docs: [OPS_ALERTING.md](OPS_ALERTING.md) (includes `stack_degraded` Beat probe).

---

## 5. Send invite (§8.15)

Use the body in [BETA_OPS_PHASE0.md §4](BETA_OPS_PHASE0.md#4-invite-email-template-manual-send)  
or [BETA_GO_LIVE.md §6](BETA_GO_LIVE.md#6-invite-email-template-phase-0).

Replace:

- `{name}` / `{license_key}`
- Feedback line → prefer **in-app + GitHub Beta bug template** (Discord optional)

H+0 checklist: [BETA_GO_LIVE.md §7](BETA_GO_LIVE.md#7-launch-day-hour-0).

### Follow-up: BETA TEST INFO (post-invite)

Send the same **getting-started flow** as [henna index](https://streamclip-henna.vercel.app/) and the invite pack, with subject **BETA TEST INFO**. **Reuse the original keys CSV** — do not re-run `issue_beta_keys.py` (that would issue new keys).

```powershell
# cohort.csv: email,name (gitignored)
# keys: dist/phase0-invite-pack/keys.csv or tmp/beta-keys.csv from original issuance
python scripts/send_beta_test_info_emails.py --csv cohort.csv `
  --keys-csv dist/phase0-invite-pack/keys.csv
python scripts/send_beta_test_info_emails.py --csv cohort.csv `
  --keys-csv tmp/beta-keys.csv --env-file .env.beta-mail --send
```

Copy `.env.beta-mail.example` → `.env.beta-mail` and set `SMTP_PASSWORD` for
`wheres@wellium.work` (Outlook / `smtp.office365.com:587`, STARTTLS).

Subject defaults to **BETA TEST INFO**. Each body includes henna download + quickstart links and the **same** `SCPRO-…` key from the keys file.

---

## 6. After first replies

```powershell
docker compose exec api python scripts/list_support_reports.py --limit 20
```

Triage with [BETA_ON_CALL.md](BETA_ON_CALL.md) severity matrix. Update [BETA_KNOWN_ISSUES.md](BETA_KNOWN_ISSUES.md) within 24h for any cohort-wide P1.
