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

Hand someone who has **never** used qClip (Windows `.exe` path preferred):

1. Open [henna home](https://streamclip-henna.vercel.app/) → download for their OS → install → activate → make a clip
2. Capture: stuck step, missing link, wrong path, unclear warning (SmartScreen / Gatekeeper)

Operator records result here (private notes OK):

| Date | Reviewer | Stuck at step? | Fixes filed? |
|------|----------|----------------|--------------|
| 2026-07-09 | Agent fresh-reader walk (operator host) | No P0 blockers | Yes — `SCBETA`→`SCPRO` key format; `start_local.ps1` stale “exe not built”; Step 4 “beta channel” → in-app Report a bug |
| 2026-07-29 | Docs IA refresh | — | Quickstart walk retargeted off Docker-first Steps 1–4 |

**Walk evidence (historical):** `verify_stack.ps1` EXIT 0; published install/quickstart/help HTTP 200. MASTER §8.14 ✅. Re-walk against installer-first steps when next cohort expands.

---

## 3. Issue keys and invite packs (§8.15)

### Manual mode (existing cohort — inline `SCPRO-…` key)

```powershell
# cohort.csv columns: email[,name]  — do not commit (see cohort.example.csv)
Copy-Item cohort.example.csv cohort.csv   # then edit real emails
New-Item -ItemType Directory -Force -Path dist\phase0-invite-pack | Out-Null
docker compose exec -e PYTHONPATH=/app -T api python scripts/issue_beta_keys.py --csv cohort.csv `
  | Out-File -Encoding utf8 dist\phase0-invite-pack\keys.csv

.\scripts\prepare_invite_pack.ps1 -Mode Manual -KeysCsv dist\phase0-invite-pack\keys.csv
```

### Re-send safety (existing cohort)

For any re-send, **reuse the current keys CSV** and rebuild bodies. Do **not** run
`issue_beta_keys.py` again unless intentionally issuing a new cohort.

```powershell
# Local dry-run: confirms every cohort row has a key; prints only key last4.
.\scripts\prepare_invite_pack.ps1 -Mode Manual -CohortCsv cohort.csv `
  -KeysCsv tmp\beta-keys.csv -OutDir tmp\phase0-invite-pack-resend -DryRun

# Rebuild local bodies under gitignored tmp/.
.\scripts\prepare_invite_pack.ps1 -Mode Manual -CohortCsv cohort.csv `
  -KeysCsv tmp\beta-keys.csv -OutDir tmp\phase0-invite-pack-resend

# Compare tmp\phase0-invite-pack-resend\index.csv against tmp\beta-keys.csv
# by email + license_key_last4, then spot-check email bodies locally.
```

`index.csv` redacts manual license keys to `license_key_last4` for comparison.
Email body files contain full keys and must stay under gitignored `tmp/` or `dist/`.
Safe operator order: **rebuild → dry-run → compare → send**.

Testers run once before UI activate:

```bash
docker compose exec -e PYTHONPATH=/app api python scripts/import_invite_license.py \
  --key SCPRO-XXXX-XXXX-XXXX-XXXX --tier admin
```

### LemonSqueezy mode (new cohort — checkout + downloads)

See [BETA_DISTRIBUTION.md](BETA_DISTRIBUTION.md). Preflight:

```powershell
.\scripts\verify_ls_beta_config.ps1
.\scripts\prepare_invite_pack.ps1 -Mode LemonSqueezy -CohortCsv cohort.csv
```

Requires `STREAMCLIP_COMMERCE__LEMON_SQUEEZY_CHECKOUT_URL` in environment.

Output (Manual): `email,license_key,order_id,tier`. Store in password manager. Default tier is `admin`.
Pack output (gitignored): `dist/phase0-invite-pack/emails/*.txt`, redacted `index.csv`, `PACK_SUMMARY.txt`, and `SEND_CHECKLIST.txt`.

Dry run (no DB writes):

```powershell
docker compose exec -e PYTHONPATH=/app api python scripts/issue_beta_keys.py --emails you@example.com --dry-run
```

---

## 4. Ops webhook + Sentry (real envs)

**Path check (no secrets):** mock verify does **not** need `OPS_WEBHOOK_URL` set
and does **not** write `.env`.

```powershell
.\scripts\verify_ops_webhook.ps1 -Help      # usage + operator next steps
.\scripts\verify_ops_webhook.ps1 -DryRun    # python/docker/api preflight (OK if stack down)
.\scripts\verify_ops_webhook.ps1            # full mock PASS (stack must be up)
```

Expect `PASS: OPS webhook path verified`, or exit `2` SKIP with fix hints if
`api` is not running. Temporary mock listens on `host.docker.internal`.

Then paste real values into **local** `.env` and **prod** `.env.production` (never git):

```bash
OPS_WEBHOOK_URL=https://<zapier-make-catch-hook-or-json-inbox>
STREAMCLIP_OBSERVABILITY__SENTRY_DSN=https://...@o....ingest.sentry.io/...
```

Optional Resend (verified domain) — same block as [OPS_ALERTING.md](OPS_ALERTING.md):

```bash
SMTP_HOST=smtp.resend.com
SMTP_PORT=587
SMTP_USER=resend
SMTP_PASSWORD=<resend_api_key>
SMTP_FROM=alerts@your-verified-domain.example
SMTP_STARTTLS=true
BUG_REPORT_TO=ops@your-domain.example
```

Then:

```powershell
docker compose up -d api worker beat
# prod:
# docker compose -f docker-compose.prod.yml --env-file .env.production up -d
.\scripts\verify_production_secrets.ps1   # warns if webhook/Sentry/Resend incomplete
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
  --keys-csv tmp/beta-keys.csv --dry-run
python scripts/send_beta_test_info_emails.py --csv cohort.csv `
  --keys-csv tmp/beta-keys.csv
# Operator send only after rebuilt bodies match current keys:
# python scripts/send_beta_test_info_emails.py --csv cohort.csv `
#   --keys-csv tmp/beta-keys.csv --send   # requires SMTP_*
```

Subject defaults to **BETA TEST INFO**. Each body includes henna download + quickstart links and the **same** `SCPRO-…` key from the keys file.

---

## 6. After first replies

```powershell
docker compose exec api python scripts/list_support_reports.py --limit 20
```

Triage with [BETA_ON_CALL.md](BETA_ON_CALL.md) severity matrix. Update [BETA_KNOWN_ISSUES.md](BETA_KNOWN_ISSUES.md) within 24h for any cohort-wide P1.

---

## 7. Lemon Squeezy preflight (new cohorts)

Before **LemonSqueezy** invites — full checklist in [BETA_DISTRIBUTION.md](BETA_DISTRIBUTION.md):

| # | Check |
|---|--------|
| 1 | `.\scripts\prepare_beta_kit.ps1` → zip exists |
| 2 | Installer built (`publish_desktop_release.ps1`) |
| 3 | LS Lead Magnet product: files uploaded, keys on, storefront off |
| 4 | `.\scripts\verify_ls_beta_config.ps1` green |
| 5 | LS test-mode $0 checkout → key + downloads in receipt |
| 6 | Clean Windows VM: zip → `start_local.ps1` → activate LS key |
| 7 | Clean Windows VM: Manual path → `import_invite_license.py` → activate |
| 8 | Henna redeployed — no GitHub-only download links |

---

## 8. Definition of done (invite gate)

**Do not send new invites until all are true:**

- [ ] CI green on release branch
- [ ] `verify_ls_beta_config.ps1` passes (LemonSqueezy cohort)
- [ ] LS test-mode checkout completed end-to-end
- [ ] Clean Windows VM: LS path smoke (install → activate → health)
- [ ] Clean Windows VM: Manual path smoke (`import_invite_license` + activate)
- [ ] Henna `BETA_DOWNLOAD` has no broken GitHub-only links
- [ ] `prepare_invite_pack.ps1 -Mode LemonSqueezy` produces valid emails
- [ ] Rollback section in [BETA_DISTRIBUTION.md](BETA_DISTRIBUTION.md) reviewed
- [ ] Existing manual cohort still works (`-Mode Manual`)
