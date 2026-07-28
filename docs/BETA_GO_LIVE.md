# StreamClip — Beta Go-Live Checklist

**Purpose:** Single-page runbook for Phase 0 (Docker technical beta). Phase 1/2 still gated on 110% (see [`docs/MASTER_TODO.md`](MASTER_TODO.md) §3.10).  
**Last updated:** 2026-07-27  
**Companions:** [`BETA_TESTER_PLAN.md`](BETA_TESTER_PLAN.md) · [`BETA_TESTER_QUICKSTART.md`](BETA_TESTER_QUICKSTART.md) · [`BETA_OPS_PHASE0.md`](BETA_OPS_PHASE0.md) · [`BETA_ON_CALL.md`](BETA_ON_CALL.md) · [`BETA_COHORT_EXIT.md`](BETA_COHORT_EXIT.md) · [`OPS_ALERTING.md`](OPS_ALERTING.md) · [`MASTER_TODO.md`](MASTER_TODO.md) · [`GAP_ANALYSIS.md`](GAP_ANALYSIS.md)

### Status legend

| Mark | Meaning |
|------|---------|
| ✅ / 🟢 | Done / gate green — evidence recorded |
| 🟡 | Partial / informational / not blocking Phase 0 invites |
| ☐ | Open — needs operator or cohort evidence (do not invent) |
| ❌ / 🔴 | Blocker |

---

## 1. Gate status (Phase 0)

**Authoritative coverage rules:** [`docs/MASTER_TODO.md`](MASTER_TODO.md) **§3.10** (canonical command, scope, phase waivers).

| Gate | Target | Verify | Status |
|------|--------|--------|--------|
| Line coverage | `fail_under = 95` (Phase 0) / 100 (Phase 1+) | `.\scripts\verify_coverage.ps1` or `verify_stack.ps1 -WithCoverage` | 🟢 ~95–96% — gate GREEN (§3.5; re-run before Phase 1) |
| Hot-path branches | ≥85% hot paths (Phase 1+) | `scripts/verify_branch_coverage.ps1` | 🟡 ~87% measured (informational Phase 0) |
| Playwright smoke | `E2E_RUN=1` | `.\scripts\verify_stack.ps1 -RunE2E` | 🟡 optional Phase 0; required for 110% |
| Stack verify | Windows + Docker | `.\scripts\verify_stack.ps1` | ✅ required — clean-slate recorded §8 |
| License email | LS `order_created` | `tests/test_license_hardening.py` | ✅ |
| ADR-001 | Desktop packaging | `docs/ADR-001-desktop-packaging.md` | ✅ |

**Phase 0 invites:** **Sent** (2026-07-09). Engineering invite gates cleared — coverage ≥95% + clean-slate Docker verify in [`CLEAN_VM_VERIFY.md`](CLEAN_VM_VERIFY.md) / §8 (MASTER §3.8).

**Phase 0 exit:** still **open**. Fill [`BETA_COHORT_EXIT.md`](BETA_COHORT_EXIT.md) (T0 matrix, H+2 / H+24 / H+72, on-call, LS staging), then sync ticks here and MASTER §8.16. Do not mark exit green without that pack.

**Download / installer:** **v1.0.0-beta.4** — see [`BETA_DOWNLOAD.md`](BETA_DOWNLOAD.md). Windows builds are **unsigned** until EV Authenticode (MASTER §4.10 / GAP O11) — SmartScreen “More info → Run anyway”.

---

## 2. T-minus 7 days — engineering

Tracked in [`MASTER_TODO.md`](MASTER_TODO.md):

- §3.5 / §3.7 — coverage ratchet to 95% then 100% + hot-path branches
- §3.3 — Playwright smoke scope
- §3.8 — clean Windows 11 VM `verify_stack.ps1`
- §8.7 — known-issues doc current → [`BETA_KNOWN_ISSUES.md`](BETA_KNOWN_ISSUES.md)
- §8.14 — quickstart fresh-reader review → [`BETA_TESTER_QUICKSTART.md`](BETA_TESTER_QUICKSTART.md)

**Invite-gate outcome:** engineering items for Phase 0 invites are **cleared** (2026-07-09). Remaining work is cohort exit + ops leftovers (GAP O4–O7, O11–O12). Seat-release UX (O9) **shipped** — apply migration `0012` before relying on Manage seats.

---

## 3. T-minus 3 days — ops & comms

Tracked in MASTER §8.9, §8.11–§8.13, §8.19, §9.2:

| Item | Doc | Status |
|------|-----|--------|
| Beta kit / feedback channel | [`BETA_OPS_PHASE0.md`](BETA_OPS_PHASE0.md) | ✅ kit path; channel = invite placeholder |
| On-call roster | [`BETA_ON_CALL.md`](BETA_ON_CALL.md) + exit pack §1 | ☐ `OPERATOR FILL` (GAP O5) |
| Observability | [`BETA_OBSERVABILITY.md`](BETA_OBSERVABILITY.md) | ✅ runbook |
| Ops webhook + Resend SMTP | [`OPS_ALERTING.md`](OPS_ALERTING.md) · [`.env.example`](../.env.example) | ☐ set `OPS_WEBHOOK_URL` in prod (GAP O7) |

---

## 4. T-minus 1 day — cohort

Tracked in MASTER §8.3, §8.10, §8.15:

- 5–10 Phase 0 testers (≥2 NVIDIA GPU), invite email, staging Pro keys
- Issue keys: `docker compose exec api python scripts/issue_beta_keys.py --csv cohort.csv` — see [`BETA_OPS_PHASE0.md`](BETA_OPS_PHASE0.md)
- Import before UI activate: `import_invite_license.py` (see quickstart)
- ~~Flip BETA_TESTER_PLAN Draft → Active~~ ✅ (§8.10)
- Keys in operator DB: ✅ 8/8 (SESSION_STATE); confirm email bodies vs `tmp/beta-keys.csv` before any re-send (GAP O6)

---

## 5. Phase 0 kit contents

**Creators (primary):** [Download page](BETA_DOWNLOAD.md) on Vercel → `StreamClip-Setup-win-x64.exe` from GitHub Releases.

**Docker self-host (technical beta):** private link, encrypted zip, or:

```powershell
.\scripts\prepare_beta_kit.ps1
# → dist/streamclip-beta-kit-<commit>-<timestamp>.zip
```

Kit includes:

1. `docs/BETA_TESTER_QUICKSTART.md`
2. `.env.example` and `.env.production.example` (MinIO + Ollama + distribution BYO OAuth)
3. `scripts/verify_stack.ps1` and `scripts/verify_coverage.ps1`
4. `docs/BETA_TESTER_PLAN.md` §4.3 flows (T0-1 … T0-6)
5. `docs/BETA_KNOWN_ISSUES.md` + performance tolerance (+25% on `docs/PERFORMANCE.md` budgets)
6. `docker-compose.yml` / `docker-compose.prod.yml` for dev and GHCR prod paths
7. `docs/BETA_OPS_PHASE0.md` + `scripts/issue_beta_keys.py` + `scripts/list_support_reports.py` (operator)

**Recommended run:** `docker compose up -d` on Windows 11, localhost UI at `:3000`, API at `:8000`.

---

## 6. Invite email template (Phase 0)

**Subject:** StreamClip technical beta — Docker self-host (Phase 0)

Body:

> You're in the StreamClip **Phase 0** cohort (technical self-host).
>
> **Goal:** Run the full clip pipeline locally and report breakages.
> **Time:** ~15 min setup, ~1 h first real job (GPU recommended).
>
> 1. Clone/access: `[REPO_OR_ZIP]`
> 2. Follow `docs/BETA_TESTER_QUICKSTART.md`
> 3. Run `.\scripts\verify_stack.ps1` — must exit 0 before your first job
> 4. Complete flows T0-1 through T0-4 in `docs/BETA_TESTER_PLAN.md`
> 5. Post feedback in `[DISCORD_OR_DISCUSSIONS]` using the pinned template
> 6. If you received a Pro/cohort key: import per quickstart (`import_invite_license`), then **Settings → License**
>
> **Commerce note:** Beta validates a **buy-once, run-local** model (no metered cloud). Pro keys are optional for T0-6.
>
> Thanks — your logs directly shape launch quality.

**Re-send rule:** Rebuild or confirm the invite pack against current keys (`tmp/beta-keys.csv` / `cohort.csv`) before any re-send (GAP O6). Do not ship stale key bodies.

---

## 7. Launch day (Hour 0)

| Time | Action | Status | Evidence |
|------|--------|--------|----------|
| H+0 | Send invites; monitor in-app bugs + GitHub beta-bug template | ✅ invites sent 2026-07-09 | Go-live / email log |
| H+2 | Confirm ≥3 testers passed T0-1 (`verify_stack` + `/api/health/stack`) | ☐ | Fill [`BETA_COHORT_EXIT.md`](BETA_COHORT_EXIT.md) §2–§3 |
| H+24 | Triage P0/P1; publish known-issues addendum if needed | ☐ | Exit pack §2 + [`BETA_KNOWN_ISSUES.md`](BETA_KNOWN_ISSUES.md) |
| H+72 | Go/no-go for expanding cohort ([`BETA_TESTER_PLAN.md`](BETA_TESTER_PLAN.md) §4.5, MASTER §8.16) | ☐ | Exit pack §2 / §5–§6 |

---

## 8. Clean VM verification record

Fill after [`CLEAN_VM_VERIFY.md`](CLEAN_VM_VERIFY.md) on each platform. **Required before external invites** (already satisfied for Windows).

| Field | Windows 11 VM | macOS (Docker beta) |
|-------|---------------|---------------------|
| Date | 2026-07-09 | _YYYY-MM-DD_ |
| Commit SHA | `6ca96b94284a4c98d9254dea98526fcfdd18041d` (+ local gate fixes) | same |
| GPU / CPU | Operator host + Docker Desktop WSL2 (clean-slate `down -v`; Hyper-V N/A) | e.g. M2 / Docker CPU |
| `verify_stack.ps1` exit | 0 PASS | _pending_ |
| First job (1h VOD) wall time | _not recorded_ | _min_ |
| Operator sign-off | ✅ (see `CLEAN_VM_VERIFY.md` latest sign-off) | ☐ |

**Phase 0 exit metrics** (MASTER §8.16) — authoritative fillable copy: [`BETA_COHORT_EXIT.md`](BETA_COHORT_EXIT.md) §5:

| Metric | Status |
|--------|--------|
| ≥4/5 testers complete T0-1 … T0-4 | ☐ outstanding |
| No open 🔴 blockers > 7 days | ☐ track in on-call |
| Line coverage ≥95% (`verify_coverage.ps1`) | ✅ met |
| Clean-VM rows above signed off | ✅ Windows 2026-07-09; macOS optional Phase 0 |
| Staging Lemon Squeezy purchase → activate → Pro | ☐ |

**Then:** Open Phase 1 per [`BETA_TESTER_PLAN.md`](BETA_TESTER_PLAN.md) §5 — still requires full **110%** coverage row (MASTER §3.10).

---

## 9. Rollback

If a show-stopper ships after invites:

1. Pin testers to last known-good image tag / commit SHA in the kit README
2. Post incident summary + workaround within **4h** ([`BETA_ON_CALL.md`](BETA_ON_CALL.md))
3. Do **not** expand cohort until T0-1 pass rate restored
4. Record incident + resolution in [`BETA_COHORT_EXIT.md`](BETA_COHORT_EXIT.md) evidence notes

---

## 10. Operator-only remaining (do not fake)

| ID | Item | Where |
|----|------|--------|
| O4 | H+2 / H+24 / H+72 + T0 evidence | [`BETA_COHORT_EXIT.md`](BETA_COHORT_EXIT.md) |
| O5 | On-call names | Exit pack §1 · [`BETA_ON_CALL.md`](BETA_ON_CALL.md) |
| O6 | Invite pack vs keys before re-send | ✅ keys match 8/8 — re-send bodies in `tmp/phase0-invite-pack-resend/` ([`tmp/invite-pack-status.md`](../tmp/invite-pack-status.md)); do **not** re-issue keys |
| O7 | Set `OPS_WEBHOOK_URL` in prod (+ Resend path) | Docs ✅ [`OPS_ALERTING.md`](OPS_ALERTING.md) · `.\scripts\verify_ops_webhook.ps1` — ☐ operator: set URL in prod `.env`, restart api/worker/beat |
| O11 | EV Authenticode / SmartScreen | Tooling ✅ [`DESKTOP_SIGNING.md`](DESKTOP_SIGNING.md) — ☐ EV cert purchase/install; `publish_desktop_release.ps1 -RequireSigned` when ready |
| O12 | Commit loader stack + desktop publish when ready | Polish ✅ `web/components/loading/` · `tmp/loader-polish-status.md` — ☐ commit + publish (E2E optional smoke) |

---

*Checklist polish: 2026-07-27 — engineering invite path green; exit blocked on operator evidence pack.*
