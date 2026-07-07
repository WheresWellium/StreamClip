# StreamClip — Beta Tester Phase Plan

**Status:** **Active (Phase 0 — Docker self-host)** · **Gate:** line ≥95% + stack verify (see §1) · **Source:** `docs/MASTER_TODO.md`
**Last updated:** 2026-07-07 · Owner: core team

This plan defines *when* beta opens, *who* gets in, *what* they run, and *how* we
know beta succeeded — aligned with MASTER_TODO release readiness and a
**Gigapixel-style one-time purchase** model (buy once, run locally, no metered cloud).

---

## 1. Entry gate — “110% coverage” (do not invite testers before this)

Line coverage caps at 100%. **110%** means:

| Milestone | Gate | Current (2026-07-07) |
|-----------|------|----------------------|
| Line coverage | `fail_under = 100` in `.coveragerc` | **95%** (`fail_under = 95`) — Phase 0 open; ratchet continues |
| Hot-path branches | ≥85% branch on: `core/tasks/pipeline_tasks.py`, `backend/services/sse.py`, `core/distribution/*`, `backend/services/job_service.py` | In progress (MASTER_TODO §3.7) |
| E2E smoke | Playwright: create job → list jobs → publish validation behind `E2E_RUN=1` | ✅ scaffold (`web/e2e/happy-path.spec.ts`); optional via `verify_stack.ps1 -RunE2E` |
| Stack verify | `scripts/verify_stack.ps1` green on Windows + Docker | ✅ server-profile tests (`-m "not desktop"`) + `/api/health/stack` |

**Ratchet order:** 95 → 100 line → branch hot paths → Playwright smoke → flip
`docs/BETA_TESTER_PLAN.md` status to **Active** and send first invites.

---

## 2. Pre-beta blockers (from MASTER_TODO — must be green or explicitly waived)

### 🔴 Hard blockers (no external testers)

| ID | Item | Beta impact if skipped |
|----|------|------------------------|
| 3.5 / 3.7 | 110% coverage gate | Regressions burn tester trust; support load explodes |
| 2.3 | License key delivery email (LS `order_created` fallback) | Paid beta / Pro testers cannot activate | ✅ Done |
| 2.4 / 2.5 | License chain (purchase → key → activate → tier) | Commerce broken; waivable only for **free** Phase 0 |
| 4.0 | Sign off ADR-001 (embedded runtime vs Docker) | ✅ Accepted 2026-07-07 — Phase 2 scope defined |

### 🟡 Soft blockers (waivable per phase with documented risk)

| ID | Item | Phase 0 | Phase 1 | Phase 2 |
|----|------|---------|---------|---------|
| 3.3 | Playwright E2E | Waive | Required | Required |
| 2.1 | TikTok direct publish (app audit) | Waive (inbox flow OK) | Waive | Required for TikTok promise |
| 2.10 | Cloud tenant stub | Waive (not in beta path) | Waive | Waive |
| 4.13 | Electron shell fixes | N/A | Partial OK | Required |

---

## 3. Beta phases overview

```
110% gate ──► Phase 0 ──► Phase 1 ──► Phase 2 ──► Public launch
              Docker       Images/       Desktop
              self-host    hosted        .exe
              (5–10)       (20–40)       (50–100)
```

| Phase | Audience | Deliverable | MASTER_TODO anchor |
|-------|----------|-------------|-------------------|
| **0 — Technical** | Devs, power users, friends | `docker compose up` + README + verify script | §1 done, §3.5 110%, distribution runbook |
| **1 — Creator closed** | Streamers / editors | GHCR images *or* single hosted URL; Pro license keys | §2.3 email, §3.3 E2E, §6 docs |
| **2 — Desktop closed** | Non-Docker creators | Signed installer + sidecar (ADR-001) | §4.1–4.13, §4.12 license UX |

**Parallel track:** Phase 0 can start at **100% line + branch hot paths** if Playwright
is still in flight; Phase 1/2 require full **110%** row in §1.

---

## 4. Phase 0 — Docker self-host beta (technical cohort)

**Goal:** Prove full pipeline + distribution on real hardware without packaging work.

### 4.1 Cohort

- **Size:** 5–10 testers
- **Profile:** Comfortable with Docker, env vars, logs, `docker compose exec`
- **Hardware:** Windows 10/11; at least 2 with NVIDIA GPU (NVENC path)

### 4.2 Tester kit (ship as a zip + private repo link)

1. `docs/BETA_TESTER_QUICKSTART.md` — 15-minute path (see also `docs/BETA_GO_LIVE.md`)
2. `.env.example` filled for local MinIO + Ollama + distribution BYO OAuth
3. `scripts/verify_stack.ps1` — must pass before first job
4. Known-issues list (`docs/BETA_KNOWN_ISSUES.md`: TikTok inbox-only, no Instagram, CPU fallback slow)
5. Feedback channel: GitHub Discussions *or* Discord `#beta-bugs` + template

### 4.3 Required tester flows (acceptance)

| # | Flow | Pass criteria |
|---|------|---------------|
| T0-1 | Install stack | `verify_stack.ps1` exit 0; `/api/health/stack` OK |
| T0-2 | Create job from URL | Job reaches `done`; ≥1 clip with preview |
| T0-3 | Edit + approve | Patch boundaries/title; approve clip |
| T0-4 | YouTube OAuth + publish | Connection saved; publish reaches `published` or clear error |
| T0-5 | Vault save | Clip saved to vault; quota respected |
| T0-6 | License activate (optional) | `SCPRO-…` key → Pro tier on distribution gates |

### 4.4 Performance SLIs (informal — from `docs/PERFORMANCE.md`)

Collect from testers (spreadsheet or form):

- 1h VOD → 5 clips: GPU **< 20 min**, CPU **< 90 min** (beta tolerance +25%)
- API create-job **< 500 ms** on localhost
- Zero “stuck in processing” without error message > 30 min

### 4.5 Exit criteria → Phase 1

- [ ] ≥4/5 testers complete T0-1..T0-4
- [ ] No 🔴 blocker bugs open > 7 days
- [ ] License chain verified with at least one real LS test purchase (§2.3)
- [ ] 110% coverage gate met

---

## 5. Phase 1 — Creator closed beta (hosted or GHCR)

**Goal:** Creators who will not touch Docker can run StreamClip with minimal support.

### 5.1 Delivery options (pick one for beta)

| Option | Pros | Cons | MASTER_TODO |
|--------|------|------|-------------|
| **A — GHCR compose** | No ops bill; testers pull pinned tags | Still requires Docker | §4.14 prod compose gaps |
| **B — Single VPS + URL** | Lowest friction for creators | You pay host + GPU; conflicts with buy-once unless **beta-only** | §2.10 cloud (defer multi-tenant) |

**Recommendation:** **Option A** for beta (aligns with self-host + one-time purchase).
Option B only for 3–5 “design partner” creators if GPU donation is acceptable.

### 5.2 Cohort

- **Size:** 20–40 (after Phase 0 exit)
- **Profile:** Twitch/YouTube creators, 2–10h VOD/week
- **Recruitment:** Waitlist form (hardware, OS, GPU, content type)

### 5.3 Commerce (one-time purchase alignment)

Before Phase 1 paid invites:

| Decision | Recommended for Gigapixel-like |
|----------|------------------------------|
| License term | **Perpetual** or major-version (not 365-day JWT default) |
| Lemon Squeezy product | One-time SKU, not subscription |
| Beta pricing | Free Pro for beta period **or** discounted lifetime key |
| Docs | Fix README “zero-subscription” vs `COMMERCIAL.md` annual mismatch |

Code touchpoints: `COMMERCIAL.md`, `core/licensing.py` (`expires_at`), LS product config.

### 5.4 Required tester flows

All Phase 0 flows plus:

| # | Flow | Pass criteria |
|---|------|---------------|
| T1-1 | Onboarding wizard | Completes; device persisted |
| T1-2 | Batch approve + batch publish | Queue shows jobs; Beat fires scheduled posts |
| T1-3 | Asset upload + overlay | Custom GIF/PNG appears on clip |
| T1-4 | Webhook (optional) | Job/clip webhook received at tester URL |
| T1-5 | Splice merge | Crossfade or cut export plays correctly |

### 5.5 Support model

- **Response SLA:** best-effort 48h weekdays
- **Severity:** 🔴 pipeline dead / data loss → same-day; 🟡 UX / publish flake → 48h
- **Office hours:** 1× weekly 30-min group call (optional)
- **No** 24/7 on-call until post-launch

### 5.6 Exit criteria → Phase 2

- [ ] ≥70% cohort completes T1-1..T1-3
- [ ] Playwright E2E green in CI (§3.3)
- [ ] ADR-001 signed; §4.2 in-process worker seam merged
- [ ] Median GPU job time within PERFORMANCE.md targets on reference clip

---

## 6. Phase 2 — Desktop `.exe` closed beta

**Goal:** Validate ADR-001 embedded runtime with non-technical users.

**Prerequisite:** MASTER_TODO §4.1–4.8 minimum (SQLite, in-process worker, bundled
ffmpeg, PyInstaller sidecar, static UI, first-run model download).

### 6.1 Cohort

- **Size:** 50–100 (staggered waves of 15)
- **Profile:** Phase 1 volunteers + new waitlist; **no Docker required**

### 6.2 Tester kit

1. Signed installer (Inno Setup or MSIX) — unsigned OK for wave 1 **with SmartScreen warning doc**
2. First-run checklist: models download, workspace path, GPU detected?
3. License activation in Settings (§4.12)
4. Uninstall / reset DB instructions

### 6.3 Required flows

| # | Flow | Pass criteria |
|---|------|---------------|
| T2-1 | Install + first launch | App opens; health green without manual env |
| T2-2 | Offline-ish job | Job completes with bundled ffmpeg + local storage |
| T2-3 | Pro activation | Key works offline after first activate |
| T2-4 | Auto-update stub | Document manual update path until 4.10 done |

### 6.4 Exit criteria → public launch

- [ ] Crash-free sessions **> 98%** (7-day window, Sentry or equivalent)
- [ ] Install → first clip **< 45 min** including model download (median)
- [ ] Code signing + installer (§4.10) for public build
- [ ] macOS port scoped (§5) — beta can remain Windows-only

---

## 7. Feedback & telemetry (privacy-first)

| Data | Phase 0 | Phase 1 | Phase 2 | Opt-in? |
|------|---------|---------|---------|---------|
| Bug reports (manual) | Required | Required | Required | — |
| Job timing / stage metrics | Encouraged | Encouraged | Default off | Yes |
| Crash dumps | No | Optional | Yes | Yes |
| Source URLs / clip content | **Never** collect | **Never** | **Never** | — |

Use existing `POST /api/feedback` + structured GitHub issues. Prometheus stays local
unless tester enables phone-home (future).

---

## 8. Roles & checklist (internal)

| Role | Responsibility |
|------|----------------|
| **Beta lead** | Cohort, comms, exit criteria |
| **Eng on-call** | 🔴 pipeline blockers |
| **Ops** | GHCR tags, LS keys, OAuth app quotas |
| **Docs** | Quickstart, known issues, changelog per wave |

### Week-before-invite checklist

- [ ] Coverage 110% green in CI
- [ ] `verify_stack.ps1` on clean VM
- [ ] Changelog / known issues published
- [ ] LS test purchase → key → activate end-to-end
- [ ] OAuth redirect URIs match deployed `WEB_ORIGIN`
- [ ] Beat + worker documented for scheduled publish testers

---

## 9. Timeline (dependency-aware, not calendar promises)

```
Now ──► 95% line ──► 100% line ──► branch hot paths ──► Playwright smoke
                                                              │
                                                              ▼
                                                    Phase 0 invites (5–10)
                                                              │
                              2.3 license email + Phase 0 exit │
                                                              ▼
                                                    Phase 1 invites (20–40)
                                                              │
                              ADR sign + §4.2–4.8 desktop MVP │
                                                              ▼
                                                    Phase 2 waves (50–100)
                                                              │
                              §4.10 signing + 2.1 TikTok audit │
                                                              ▼
                                                    Public launch
```

---

## 10. MASTER_TODO cross-reference

| Beta need | MASTER_TODO |
|-----------|-------------|
| Coverage gate | §3.5, §3.7 |
| E2E | §3.3 |
| License / commerce | §2.3–2.5, §4.12 |
| Distribution | §2.1, §2.19, runbook |
| Desktop | §4.0–4.13, ADR-001 |
| macOS (post-beta) | §5 |
| Docs / env | §6 |

When this plan changes, update the row in `docs/MASTER_TODO.md` §8.
