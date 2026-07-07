# StreamClip — Beta Go-Live Checklist

**Purpose:** Single-page runbook for Phase 0 (Docker technical beta). Phase 1/2 still gated on 100% line + branch coverage.  
**Companion docs:** `docs/BETA_TESTER_PLAN.md`, `docs/BETA_TESTER_QUICKSTART.md`, `docs/MASTER_TODO.md`

---

## 1. Gate status (Phase 0)

| Gate | Target | Verify | Status |
|------|--------|--------|--------|
| Line coverage | `fail_under = 100` (Phase 1+) | `docker compose exec -T api pytest tests/ -m "not desktop" --cov=backend --cov=core` | ✅ 95% — Phase 0 waived |
| Hot-path branches | ≥85% hot paths (Phase 1+) | §3.7 branch cov | 🟡 in progress |
| Playwright smoke | `E2E_RUN=1` | `.\scripts\verify_stack.ps1 -RunE2E` | ✅ optional |
| Stack verify | Windows + Docker | `.\scripts\verify_stack.ps1` | ✅ required |
| License email | LS `order_created` | `tests/test_license_hardening.py` | ✅ |
| ADR-001 | Desktop packaging | `docs/ADR-001-desktop-packaging.md` | ✅ |

**Phase 0 Docker beta:** **OPEN** as of 2026-07-07. Invite 5–10 technical testers after `verify_stack.ps1` passes locally.

---

## 2. T-minus 7 days — engineering

- [ ] Ratchet `.coveragerc` to 100; rebuild API image: `docker compose build api && docker compose up -d api --force-recreate`
- [ ] Branch coverage tests merged for hot paths (see `docs/MASTER_TODO.md` §3.7)
- [ ] Playwright smoke covers: health → create job (202) → list jobs → batch publish validation
- [ ] `verify_stack.ps1` passes on a **clean** Windows 11 VM (Docker Desktop, no prior workspace)
- [ ] Known-issues doc updated (TikTok inbox-only, CPU fallback SLAs)
- [ ] `docs/BETA_TESTER_QUICKSTART.md` reviewed by someone who has never run the repo

---

## 3. T-minus 3 days — ops & comms

- [ ] Private GitHub repo or zip kit prepared (see §5)
- [ ] Discord `#beta-bugs` or GitHub Discussions category live
- [ ] Feedback template pinned (job id, GPU model, logs snippet, steps)
- [ ] On-call rotation named for first 72h (P0 = pipeline stuck, auth broken, data loss)
- [ ] Prometheus/Grafana or log tail procedure documented for testers who opt in

---

## 4. T-minus 1 day — cohort

- [ ] **5–10** Phase 0 testers confirmed (≥2 with NVIDIA GPU)
- [ ] Invite email drafted (§6)
- [ ] Pro license keys ready for optional T0-6 (`SCPRO-…` staging keys)
- [ ] Flip `docs/BETA_TESTER_PLAN.md` status **Draft → Active**

---

## 5. Phase 0 kit contents

Ship via private link or encrypted zip:

1. `docs/BETA_TESTER_QUICKSTART.md`
2. `.env.example` (MinIO + Ollama + distribution BYO OAuth)
3. `scripts/verify_stack.ps1`
4. `docs/BETA_TESTER_PLAN.md` §4.3 flows (T0-1 … T0-6)
5. Known issues + performance tolerance (+25% on `docs/PERFORMANCE.md` budgets)

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
>
> **Commerce note:** Beta validates a **buy-once, run-local** model (no metered cloud). Pro keys are optional for T0-6.  
>
> Thanks — your logs directly shape launch quality.

---

## 7. Launch day (Hour 0)

| Time | Action |
|------|--------|
| H+0 | Send invites; monitor `#beta-bugs` |
| H+2 | Confirm ≥3 testers passed T0-1 (`verify_stack` + `/api/health/stack`) |
| H+24 | Triage P0/P1; publish known-issues addendum if needed |
| H+72 | Go/no-go for expanding cohort (see `BETA_TESTER_PLAN.md` §4.5) |

---

## 8. Success metrics (Phase 0 exit)

- ≥4/5 testers complete T0-1 … T0-4
- No open 🔴 blockers > 7 days
- 110% gate green on `main`
- At least one staging Lemon Squeezy purchase → activate → Pro tier verified

**Then:** Open Phase 1 (creator closed, GHCR or hosted URL) per `docs/BETA_TESTER_PLAN.md` §5.

---

## 9. Rollback

If a show-stopper ships after invites:

1. Pin testers to last known-good image tag / commit SHA in the kit README
2. Post incident summary + workaround within 4h
3. Do **not** expand cohort until T0-1 pass rate restored

---

*Last updated: 2026-07-06*
