# qClip — Beta Go-Live Checklist

**Purpose:** Single-page runbook for Phase 0 (Docker technical beta). Phase 1/2 still gated on 110% (see [`docs/MASTER_TODO.md`](MASTER_TODO.md) §3.10).  
**Companion docs:** `docs/BETA_TESTER_PLAN.md`, `docs/GET_STARTED.md`, `docs/MASTER_TODO.md`

---

## 1. Gate status (Phase 0)

**Authoritative coverage rules:** [`docs/MASTER_TODO.md`](MASTER_TODO.md) **§3.10** (canonical command, scope, phase waivers).

| Gate | Target | Verify | Status |
|------|--------|--------|--------|
| Line coverage | `fail_under = 95` (Phase 0) / 100 (Phase 1+) | `.\scripts\verify_coverage.ps1` or `verify_stack.ps1 -WithCoverage` | 🟢 95.40% — gate GREEN (§3.5, 2026-07-07) |
| Hot-path branches | ≥85% hot paths (Phase 1+) | `scripts/verify_branch_coverage.ps1` | 🟡 ~87% measured (informational Phase 0) |
| Playwright smoke | `E2E_RUN=1` | `.\scripts\verify_stack.ps1 -RunE2E` | ✅ optional |
| Stack verify | Windows + Docker | `.\scripts\verify_stack.ps1` | ✅ required |
| License email | LS `order_created` | `tests/test_license_hardening.py` | ✅ |
| ADR-001 | Desktop packaging | `docs/ADR-001-desktop-packaging.md` | ✅ |

**Phase 0 invites:** **Engineering gate CLEARED** (2026-07-09) — line coverage ≥95% and clean-slate `verify_stack.ps1` recorded in [`docs/CLEAN_VM_VERIFY.md`](CLEAN_VM_VERIFY.md) / MASTER §3.8. Invites were **sent** (see §7). Phase 0 **exit** still needs cohort T0 metrics (MASTER §8.16).

Current Windows desktop artifact: **v1.0.0-beta.5** (`qClip-Setup-win-x64.exe`) — see [GET_STARTED.md](GET_STARTED.md).

---

## 2. T-minus 7 days — engineering

Tracked in [`docs/MASTER_TODO.md`](MASTER_TODO.md):

- §3.5 / §3.7 — coverage ratchet to 95% then 100% + hot-path branches
- §3.3 — Playwright smoke scope
- §3.8 — clean Windows 11 VM `verify_stack.ps1`
- §8.7 — known-issues doc current
- §8.14 — quickstart fresh-reader review

---

## 3. T-minus 3 days — ops & comms

Tracked in MASTER §8.9, §8.11–§8.13, §8.19, §9.2:

- Beta kit prep, feedback channel, on-call, observability procedure

---

## 4. T-minus 1 day — cohort

Tracked in MASTER §8.3, §8.10, §8.15:

- 5–10 Phase 0 testers (≥2 NVIDIA GPU), invite email, staging Pro keys
- Issue keys: `docker compose exec api python scripts/issue_beta_keys.py --csv cohort.csv` — see [BETA_OPS_PHASE0.md](BETA_OPS_PHASE0.md)
- ~~Flip BETA_TESTER_PLAN Draft → Active~~ ✅ done (§8.10)

---

## 5. Phase 0 kit contents

**Creators (primary):** [Get started](GET_STARTED.md) on Vercel → `qClip-Setup-win-x64.exe` from invite kit or GitHub Releases (collaborators).

**Docker self-host (technical beta):** ship via private link, encrypted zip, or:

```powershell
.\scripts\prepare_beta_kit.ps1
# → dist/streamclip-beta-kit-<commit>-<timestamp>.zip
```

Kit includes:

1. `docs/GET_STARTED.md`
2. `.env.example` and `.env.production.example` (MinIO + Ollama + distribution BYO OAuth)
3. `scripts/verify_stack.ps1` and `scripts/verify_coverage.ps1`
4. `docs/BETA_TESTER_PLAN.md` §4.3 flows (T0-1 … T0-6)
5. `docs/BETA_KNOWN_ISSUES.md` + performance tolerance (+25% on `docs/PERFORMANCE.md` budgets)
6. `docker-compose.yml` / `docker-compose.prod.yml` for dev and GHCR prod paths
7. `docs/BETA_OPS_PHASE0.md` + `scripts/issue_beta_keys.py` + `scripts/list_support_reports.py` (operator)

**Recommended run (creators):** install `qClip-Setup-win-x64.exe` or `qClip-mac-arm64.dmg` from the invite kit — **no Docker**. See [DESKTOP_SOLO_GATE.md](DESKTOP_SOLO_GATE.md).  
**Operator alternative:** `docker compose up -d` → UI `:3000`, API `:8000`.

---

## 6. Invite email template (Phase 0 — desktop creators)

**Subject:** qClip beta — desktop install (no Docker)

Body:

> You're in the qClip **Phase 0** creator cohort.  
>
> **Goal:** Install the desktop app, run the clip pipeline locally, and report breakages.  
> **Time:** ~15 min setup, ~1 h first real job (GPU recommended on Windows).  
> **You do not need Docker Desktop.**  
>
> 1. Download the invite kit from `[DRIVE_OR_LS_LINK]`  
> 2. Install `installers/qClip-Setup-win-x64.exe` (Windows) or `installers/qClip-mac-arm64.dmg` (Mac)  
> 3. Follow `docs/GET_STARTED.md` (desktop steps)  
> 4. Complete flows T0-1 through T0-4 in `docs/BETA_TESTER_PLAN.md`  
> 5. Post feedback in `[DISCORD_OR_DISCUSSIONS]` using the pinned template  
>
> SmartScreen / Gatekeeper: use More info → Run anyway (Windows) or right-click → Open (Mac).  
> **Commerce note:** Beta validates a **buy-once, run-local** model (no metered cloud). Pro keys are optional for T0-6.  
>
> Thanks — your logs directly shape launch quality.

---

## 7. Launch day (Hour 0)

| Time | Action | Status |
|------|--------|--------|
| H+0 | Send invites; monitor in-app bugs + GitHub beta-bug template | ✅ invites sent 2026-07-09 |
| H+2 | Confirm ≥3 testers passed T0-1 (`verify_stack` + `/api/health/stack`) | ☐ |
| H+24 | Triage P0/P1; publish known-issues addendum if needed | ☐ |
| H+72 | Go/no-go for expanding cohort (see `BETA_TESTER_PLAN.md` §4.5, MASTER §8.16) | ☐ |

---

## 8. Clean VM verification record (required before external invites)

Fill this table after running [`docs/CLEAN_VM_VERIFY.md`](CLEAN_VM_VERIFY.md) on each platform.

| Field | Windows 11 (clean-slate Docker) | macOS (Docker beta) |
|-------|----------------------------------|---------------------|
| Date | 2026-07-09 | _YYYY-MM-DD_ |
| Commit SHA | `6ca96b94284a4c98d9254dea98526fcfdd18041d` (+ local gate fixes) | same |
| GPU / CPU | Operator host WSL2 / CPU or GPU per host | e.g. M2 / Docker CPU |
| `verify_stack.ps1` exit | 0 PASS | _outstanding_ |
| First job (1h VOD) wall time | not recorded on clean-slate day | _min_ |
| Operator sign-off | ✅ (see CLEAN_VM_VERIFY) | ☐ |

**Phase 0 exit metrics** (MASTER §8.16):

- ≥4/5 testers complete T0-1 … T0-4
- No open 🔴 blockers > 7 days
- Line coverage ≥95% (`verify_coverage.ps1`) — ✅ met
- Clean-VM Windows row **signed off** — ✅ 2026-07-09; macOS Docker row still open
- At least one staging Lemon Squeezy purchase → activate → Pro tier verified

**Then:** Open Phase 1 per [`docs/BETA_TESTER_PLAN.md`](BETA_TESTER_PLAN.md) §5.

---

## 9. Rollback

If a show-stopper ships after invites:

1. Pin testers to last known-good image tag / commit SHA in the kit README
2. Post incident summary + workaround within 4h
3. Do **not** expand cohort until T0-1 pass rate restored

---

*Last updated: 2026-07-28*
