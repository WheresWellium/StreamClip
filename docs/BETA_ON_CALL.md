# StreamClip — Beta On-Call Runbook

**Audience:** Operators running Phase 0 cohort (5–10 testers)  
**Companion:** [Beta go-live](BETA_GO_LIVE.md) (internal) · [Phase 0 ops](BETA_OPS_PHASE0.md) (internal) · [Beta test plan](BETA_TESTER_PLAN.md)  
**Last updated:** 2026-07-09

This runbook covers **keys, SMTP, webhooks, and on-call** for the Docker self-host beta. Keep secrets out of git. Fill **TBD** contact cells before sending invites — do not invent names in git.

---

## 1. Roles (operator fills before invite)

| Role | Responsibility | Name | Contact (email / phone / chat) |
|------|----------------|------|--------------------------------|
| **Beta lead** | Cohort comms, invite timing, exit criteria | TBD | TBD |
| **Eng on-call (primary)** | 🔴 P0: pipeline stuck, auth broken, data loss, stack won't start | TBD | TBD |
| **Eng on-call (backup)** | Covers primary offline / first 72h handoff | TBD | TBD |
| **Ops** | GHCR tags, license keys, OAuth app quotas | TBD | TBD |
| **Docs** | Quickstart, tutorials, known issues per wave | TBD | TBD |

**How to fill:** replace each `TBD` with a real person before H+0. Keep a private copy (password manager / ops channel) if you do not want contacts in git.

**Response SLA (Phase 0):** best-effort **48h weekdays**; 🔴 blockers **same-day**. No 24/7 until post-launch ([test plan §5.5](BETA_TESTER_PLAN.md#55-support-model)).

---

## 2. Severity matrix

| Sev | Examples | Ack | Resolve / mitigate | Who |
|-----|----------|-----|--------------------|-----|
| 🔴 **P0** | All jobs fail; auth/login broken; data loss; `verify_stack` red for cohort; stack won't start | **1h** (business hours) / same day | Same day; pause new invites | Eng primary → backup |
| 🟡 **P1** | Single-platform OAuth flake; one tester GPU OOM; install blocked for one OS | **4h** weekday | **48h** fix or documented workaround | Eng + Ops |
| 🟢 **P2** | UX copy; slow CPU jobs; TikTok inbox-only confusion; docs gaps | Next triage | **48h** reply; known-issues update | Docs + Eng |

**Feedback intake:** in-app bug/feedback → `bug_reports`; public fallback → GitHub **Beta bug report** template (`.github/ISSUE_TEMPLATE/beta-bug.yml`). See [BETA_OPS_PHASE0.md §1](BETA_OPS_PHASE0.md#1-support-channels).

---

## 3. Pre-invite checklist

Do **not** send cohort invites until all items pass — see [BETA_GO_LIVE.md §1](BETA_GO_LIVE.md#1-gate-status-phase-0) and [CLEAN_VM_VERIFY.md](CLEAN_VM_VERIFY.md):

- [ ] `verify_coverage.ps1` ≥95% green
- [ ] Clean-VM `verify_stack.ps1` recorded (§8 sign-off in go-live doc)
- [ ] [BETA_KNOWN_ISSUES.md](BETA_KNOWN_ISSUES.md) current for this wave
- [ ] Beta keys issued and stored securely
- [ ] At least one admin account for bug-report API
- [ ] OAuth redirect URIs match `WEB_ORIGIN` ([checklist](distribution-runbook.md#oauth-redirect-uri-checklist))
- [ ] Feedback channel live (in-app + GitHub template; Discord optional)
- [ ] §1 role table filled (no remaining TBD for primary/backup)

---

## 4. Issue beta license keys

Generate keys for the cohort CSV (`email,license_key,order_id,tier`):

```powershell
docker compose exec -e PYTHONPATH=/app api python scripts/issue_beta_keys.py --csv cohort.csv
# or single tester:
docker compose exec -e PYTHONPATH=/app api python scripts/issue_beta_keys.py --emails tester@example.com
```

**Default tier:** `admin` — full distribution + quotas. **Do not commit** the output CSV.

Local dev shortcut (operator machine only):

```powershell
docker compose exec api python scripts/grant_dev_pro.py
```

Send keys in the invite email body. Template: [BETA_OPS_PHASE0.md §4](BETA_OPS_PHASE0.md#4-invite-email-template-manual-send).

---

## 5. SMTP (bug report email)

Optional — reports **always persist** in Postgres first.

| Variable | Purpose |
|----------|---------|
| `SMTP_HOST` | Outbound mail server |
| `SMTP_PORT` | Usually `587` (TLS) or `465` |
| `SMTP_USER` / `SMTP_PASSWORD` | Auth |
| `SMTP_FROM` | From address |
| `BUG_REPORT_TO` | Operator inbox for bug reports |

Set on **api** and **worker** services in `.env`, then:

```powershell
docker compose up -d api worker
```

Test: submit **Report a bug** in the app; confirm row in DB and email arrival.

```powershell
docker compose exec api python scripts/list_support_reports.py --kind bug --limit 5
```

---

## 6. Ops webhook (autonomous)

Preferred when configured — forwards bug + beta feedback **and** proactive
`job_failed` / `stack_degraded` alerts to Discord/Slack/Zapier Catch Hook/custom agent inbox.

| Variable | Purpose |
|----------|---------|
| `OPS_WEBHOOK_URL` | HTTPS JSON webhook (api + worker + beat) |
| `STREAMCLIP_OBSERVABILITY__SENTRY_DSN` | Optional — Celery + API exceptions |

See internal [`OPS_ALERTING.md`](OPS_ALERTING.md). Invite-ready steps: [`BETA_INVITE_PACK.md`](BETA_INVITE_PACK.md).

Verify:

```powershell
docker compose exec api python scripts/list_support_reports.py --limit 10
```

Admin API (requires admin JWT):

```http
GET /api/admin/bug-reports?limit=50
Authorization: Bearer <admin_token>
```

`stack_degraded` fires from Beat every 5 minutes when DB/Redis/storage fail (15 min cooldown).
---

## 7. On-call playbooks

### 🔴 P0 — Pipeline dead (all jobs fail)

1. Confirm stack: `.\scripts\verify_stack.ps1`
2. Check worker: `docker compose logs worker --tail 100`
3. Restart: `docker compose restart worker api`
4. If GPU OOM: scale down concurrency or disable `--profile gpu` temporarily
5. Post status + workaround in beta channel within **4h** ([go-live §9 rollback](BETA_GO_LIVE.md#9-rollback))

### 🟡 P1 — Publish / OAuth flake

1. Confirm `TOKEN_ENCRYPTION_KEY` + `WEB_ORIGIN` on api/worker
2. Tester reconnects platform in Settings → Distribution
3. Check queue: Distribution → Queue in UI or `publish_jobs` table
4. Ensure **beat** container running for scheduled posts
5. Re-check redirect URIs match [distribution-runbook checklist](distribution-runbook.md#oauth-redirect-uri-checklist)

### 🟢 P2 — UX / docs / slow CPU jobs

1. Point tester to [Tutorials](tutorials/TUTORIAL_TROUBLESHOOTING.md)
2. Collect job ID + logs (GitHub beta-bug template fields)
3. Triage in 48h

---

## 8. Reading support reports

```powershell
docker compose exec api python scripts/list_support_reports.py --limit 20
docker compose exec api python scripts/list_support_reports.py --kind feedback
docker compose exec api python scripts/list_support_reports.py --kind bug
```

SQL fallback:

```sql
SELECT id, severity, categories, message, user_id, device_id, created_at, environment
FROM bug_reports ORDER BY created_at DESC LIMIT 50;
```

Beta feedback rows: `environment->>'kind' = 'beta_feedback'`.

---

## 9. OAuth operator tasks

Before invites:

1. Google Cloud OAuth app — redirect URI = `{WEB_ORIGIN}/api/distribution/oauth/youtube_shorts/callback` (platform id is `youtube_shorts`, not `youtube`)
2. TikTok app (optional) — `{WEB_ORIGIN}/api/distribution/oauth/tiktok/callback`; inbox scope only during beta
3. Set `STREAMCLIP_DISTRIBUTION__YOUTUBE_PUBLISH_ENABLED=true` in production `.env`
4. Generate production Fernet key — never reuse dev compose key

Full copy-paste checklist: [distribution-runbook.md](distribution-runbook.md#oauth-redirect-uri-checklist).

---

## 10. First 72 hours checklist

| Window | Action | Owner |
|--------|--------|-------|
| **H−1** | §1 roles filled; §3 pre-invite green; feedback channel + OAuth checklist done | Beta lead |
| **H+0** | Send invites; watch in-app reports + GitHub `beta` label; confirm webhook/SMTP if configured | Beta lead + Eng |
| **H+2** | Confirm ≥3 testers passed T0-1 (`verify_stack` + health) | Eng |
| **H+8** | Triage open P0/P1; post status if any P0 open >4h | Eng primary |
| **H+24** | Full triage; update [BETA_KNOWN_ISSUES.md](BETA_KNOWN_ISSUES.md) if needed | Eng + Docs |
| **H+48** | Backup on-call check-in; clear or document remaining P1s | Eng backup |
| **H+72** | Go/no-go expand cohort ([test plan §4.5](BETA_TESTER_PLAN.md#45-exit-criteria--phase-1)); pause invites on unresolved P0 | Beta lead |

---

## 11. Escalation

| Severity | Examples | Action |
|----------|----------|--------|
| 🔴 | Data loss, stack won't start, all publishes fail | Eng on-call same day; pause invites |
| 🟡 | Single-platform OAuth, one tester GPU | 48h fix or documented workaround |
| 🟢 | Copy, slow CPU, TikTok inbox | Known issues + tutorial link |

**Rollback:** Pin cohort to last good image tag; do not expand until T0-1 pass rate restored.

---

*Internal ops doc — not published on docs site.*
