# StreamClip — Consolidated Plan Registry

**Last updated:** 2026-07-27  
**Purpose:** Single index of **active work** (beta + release readiness) vs **future updates** (frozen until the active track is complete).  
**Canonical task list:** [`docs/MASTER_TODO.md`](docs/MASTER_TODO.md) · **Beta gates:** [`docs/BETA_TESTER_PLAN.md`](docs/BETA_TESTER_PLAN.md) · **Go-live:** [`docs/BETA_GO_LIVE.md`](docs/BETA_GO_LIVE.md)

---

## How to use this document

| Section | Rule |
|---------|------|
| **Active track** | Work here only. Every item maps to MASTER_TODO or BETA_TESTER_PLAN. |
| **Completed plans** | Archive — do not re-open unless a regression forces it. |
| **Future updates** | **FROZEN.** Do not start design, scaffolding, or implementation until **all** active-track exit criteria through **Beta Phase 2 + public-launch readiness (Phase 3)** are met. |

**Phase naming (this doc):**

| Label | Meaning |
|-------|---------|
| **Beta Phase 0** | Docker self-host technical cohort (5–10 testers) |
| **Beta Phase 1** | Creator closed beta (20–40; GHCR/hosted) |
| **Beta Phase 2** | Desktop `.exe` closed beta (50–100; no Docker required) |
| **Phase 3** | Public launch readiness — exit Phase 2 + signing + ops hardening |

---

## Active track — work here first

### Gate status (2026-07-09 reality; PLAN sync 2026-07-27)

| Gate | Status | Blocks |
|------|--------|--------|
| Line coverage ≥95% (`verify_coverage.ps1`) | **GREEN** (**96%** / 372 miss; SkipBuild 2026-07-27) | — |
| Clean-VM / clean-slate `verify_stack.ps1` (MASTER §3.8 / FS-2.4) | **PASS** 2026-07-09 (clean-slate Docker `down -v`; Hyper-V N/A) | — (invite gate cleared) |
| Phase 0 invites | **SENT** 2026-07-09 (`BETA_GO_LIVE` §1 / §7 H+0) | — |
| 110% coverage (100% line + branches + E2E) | Not met | Beta Phase 1 |
| EV code-signing + signed desktop release (§4.10) | Outstanding | Beta Phase 2 |
| macOS DMG codesign + notarization (§5.3) | Outstanding | Beta Phase 2 exit (scoped) |

---

### Beta Phase 0 — Docker self-host (current focus: H+0 monitoring)

**Status:** Engineering invite gates cleared; **invites SENT** 2026-07-09. Now **H+0 monitoring** per [`BETA_GO_LIVE.md` §7](docs/BETA_GO_LIVE.md).  
**Exit criteria:** [`BETA_TESTER_PLAN.md` §4.5](docs/BETA_TESTER_PLAN.md) / MASTER §8.16 (still open).

| ID | Item | Source | Status |
|----|------|--------|--------|
| P0-1 | **Clean-VM / clean-slate `verify_stack.ps1`** (Windows; Hyper-V N/A → clean-slate Docker) | FS-2.4, MASTER §3.8 | ✅ 2026-07-09 |
| P0-2 | Alembic `upgrade head` on every deploy (head `0010_password_reset_tokens`) | MASTER §1.2 | 🟡 ongoing |
| P0-3 | Phase 0 cohort prep: feedback channel, on-call, OAuth URIs, invite comms | MASTER §8.11–8.15 | ✅ 2026-07-09 |
| P0-4 | Quickstart fresh-reader review | MASTER §8.14 | ✅ 2026-07-09 |
| P0-5 | Run Phase 0 cohort (5–10); T0-1..T0-4 flows | MASTER §8.3 | 🟡 invites SENT; cohort in flight |
| P0-6 | Phase 0 exit sign-off (≥4/5 complete T0 flows; no 🔴 >7d; LS test purchase) | MASTER §8.16 | ⬜ |

**Open MASTER items that affect Phase 0:**

| ID | Item | Sev |
|----|------|-----|
| 8.3 | Phase 0 cohort T0 flows (invites out; results outstanding) | 🟡 |
| 8.16 | Phase 0 exit sign-off (T0 + H+72 go/no-go) | 🟡 |
| 2.1 | TikTok **direct** publish (inbox flow ✅; app audit pending) | 🟡 |

---

### Beta Phase 1 — Creator closed beta

**Prerequisite:** Phase 0 exit + **110% coverage gate** (MASTER §8.1).

| ID | Item | Source | Status |
|----|------|--------|--------|
| P1-1 | Ratchet line coverage toward 100% — **96%** / 372 stmts remaining (§3.10; gate GREEN at 95) | MASTER §3.5, §3.10 | ⬜ |
| P1-2 | Hot-path branch coverage ≥85% + enforce in CI | MASTER §3.7 | ⬜ |
| P1-3 | ~~Playwright CI green (§3.3)~~ ✅ `e2e` job in `test.yml` (`E2E_RUN=1`); 12/12 PASS 2026-07-09 | MASTER §3.3, §8.17 | ✅ |
| P1-4 | GHCR `images.yml` + `STREAMCLIP_IMAGE_PREFIX` ✅; **first operator tag/dispatch still open** (`PRODUCTION.md` §8) | MASTER §8.8 | 🟡 |
| P1-5 | Phase 1 cohort (20–40 creators) | MASTER §8.4 | ⬜ |
| P1-6 | Phase 1 exit (≥70% T1 flows; GPU perf within SLA) | MASTER §8.17 | ⬜ |

---

### Beta Phase 2 — Desktop closed beta

**Prerequisite:** Phase 1 exit + desktop signing minimum (§4.10).

| ID | Item | Source | Status |
|----|------|--------|--------|
| P2-1 | Purchase EV cert + **first signed Windows release** | MASTER §4.10 | ⬜ |
| P2-2 | GitHub Releases publish for auto-update | MASTER §4.10 | ⬜ |
| P2-3 | macOS: VideoToolbox ffmpeg (§5.1) | MASTER §5.1 | ⬜ |
| P2-4 | macOS: Torch MPS + arm64 Whisper wheels (§5.2) | MASTER §5.2 | ⬜ |
| P2-5 | macOS: codesign + notarization + Gatekeeper (§5.3) | MASTER §5.3 | ⬜ |
| P2-6 | Phase 2 cohort waves (50–100 testers) | MASTER §8.5 | ⬜ |
| P2-7 | Phase 2 exit: crash-free >98% (7d); install→first clip <45m | MASTER §8.18 | ⬜ |

**macOS scaffold already shipped:** §5.4 paths, §5.5 arm64 naming, `build_desktop_installer_macos.sh`, `MACOS.md`.

---

### Phase 3 — Public launch readiness

**Prerequisite:** Phase 2 exit.

| ID | Item | Source | Status |
|----|------|--------|--------|
| P3-1 | Confirm Lemon Squeezy product config in dashboard | MASTER §8.6 | ⬜ |
| P3-2 | Prometheus/Grafana or log-tail procedure for opt-in testers | MASTER §9.2 | ⬜ |
| P3-3 | ~~Resolve or remove `backend/cloud/tenant.py` multi-tenant stub~~ ✅ Removed 2026-07-09 | MASTER §2.10 | ✅ |
| P3-4 | FS-3 deferred consolidation (presign helper, OAuth base, etc.) | MASTER §FS-3 | ⬜ |
| P3-5 | Week-before-invite checklist (`BETA_TESTER_PLAN` §8 / MASTER §8.19): §3.5/§3.8/OAuth/Beat/known-issues ✅; **still open:** LS E2E purchase (operator) · 110% CI (§3.11, Phase 1+) | MASTER §8.19 | 🟡 |

---

## Completed plans (archive — do not re-open)

These Cursor plans are **fully built** or superseded by shipped code. Reference only.

| Plan | Location | Outcome |
|------|----------|---------|
| Stack-first build | `.cursor/plans/streamclip_stack_build_24bac5fb.plan.md` | ✅ Monorepo, Docker, stub→real pipeline |
| Production bring-up Phases 0.5–9 | `.cursor/plans/streamclip_production_bring-up_670b78c3.plan.md` | ✅ Smoke, hardening, UI, tests, deploy docs |
| Feature roadmap P0–P3 | `.cursor/plans/streamclip_feature_roadmap_5bd3ae26.plan.md` | ✅ Editor, splice, vault, distribution, commerce |
| Product packaging | `.cursor/plans/streamclip_product_packaging_a9e8ec9f.plan.md` | ✅ Licensing, LS, Electron, prod compose |
| MASTER consolidation | `PLAN.md` (2026-07-07 entry) | ✅ Coverage truth, doc sync, FS-1 audit fixes |

---

## Future updates — FROZEN until active track complete

> **Policy:** Nothing in this section may be started until **P0-6 through P3-5** (or explicit team sign-off that the active track is done).  
> Agents and contributors: if a task below looks urgent, **add it to MASTER_TODO §Future** — do not implement.

**Unlock condition:** Beta Phase 2 exit **and** Phase 3 public-launch checklist signed off in `BETA_TESTER_PLAN.md`.

---

### F1. AI model router foundation (Phase 1 of AI plan)

**Source:** `.cursor/plans/streamclip_ai_models_975144ab.plan.md` — tasks `p1-*`

| Task | Description | Status |
|------|-------------|--------|
| F1-1 | `docs/ai/use_case_spec.md` — success tenets, latency budgets, degrade policies | ⬜ |
| F1-2 | `core/llm/` — extract providers from `core/virality.py`; tiered LLMRouter + fallbacks | ⬜ |
| F1-3 | `core/inference/` — protocols + local wrappers (Whisper/YOLO/embeddings) | ⬜ |
| F1-4 | Extend `LLMConfig` + `InferenceBackendConfig`; freeze routes in `config_snapshot` | ⬜ |
| F1-5 | `/api/health/llm`, Prometheus metrics, router tests | ⬜ |

**Why frozen:** Router work is valuable but not on the Phase 0 exit / Phase 1 critical path; virality already degrades safely today.

---

### F2. Virality ranker fine-tune (Phase 2 of AI plan)

**Source:** `.cursor/plans/streamclip_ai_models_975144ab.plan.md` — tasks `p2-*`

| Task | Description | Status |
|------|-------------|--------|
| F2-1 | `scripts/export_training_corpus.py` from opt-in `export_training_bundle` | ⬜ |
| F2-2 | SageMaker direct fine-tune virality ranker (train → evaluate → deploy) | ⬜ |
| F2-3 | `sagemaker_ranker` LLM provider; shadow → canary → promote | ⬜ |

**Prerequisite inside future track:** F1 complete + sufficient opt-in corpus volume.

---

### F3. SageMaker hybrid inference (full cloud scale)

**Source:** `.cursor/plans/streamclip_sagemaker_integration_4894fa37.plan.md` — **all todos pending**

| Phase | Scope | Status |
|-------|-------|--------|
| S0 | AWS IaC, dual-bucket IAM, dev/staging/prod profiles | ⬜ |
| S1 | `core/inference/` router, circuit breaker, manifest, metrics | ⬜ |
| S1b | Golden-file parity suite (local vs mocked SM) | ⬜ |
| S2A | Whisper async endpoint + Celery poll | ⬜ |
| S2B | YOLO async crop-path endpoint | ⬜ |
| S2C | Embeddings + Feature Store cache hierarchy | ⬜ |
| S4 | Training data: publish analytics, export v2 | ⬜ |
| S5 | Virality ranker SFT + shadow/canary | ⬜ |
| S6 | Style-learning reinforcement loop | ⬜ |
| S7 | Diarization async endpoint | ⬜ |
| S8–S9 | `config/cloud.yaml`, UI transparency, runbooks, cost dashboards | ⬜ |

**Overlap note:** F1/F2 and S1/S5 overlap — execute **once** under AI plan after unlock; SageMaker plan is the cloud-ops superset.

---

### F4. New intelligence surfaces (Phase 4–5 of AI plan)

**Source:** `.cursor/plans/streamclip_ai_models_975144ab.plan.md` — tasks `p4-*`, `p5-*`

| Task | Description | Status |
|------|-------------|--------|
| F4-1 | Premium-tier `clip_title` LLM task (post-hoc hooks) | ⬜ |
| F4-2 | UI transparency — expose model route + version on clips | ⬜ |
| F4-3 | `style_learning` v2 from ranker + analytics | ⬜ |
| F4-4 | Optional `run_diarize` stage (podcast/IRL) | ⬜ |
| F5-1 | Weekly retrain loop, cost/SLO dashboards | ⬜ |
| F5-2 | `docs/ai/ROUTER.md` + TDD §AI sync | ⬜ |

---

### F5. Product roadmap — CREATOR_PLATFORM “Later”

**Source:** [`docs/CREATOR_PLATFORM.md`](docs/CREATOR_PLATFORM.md) · MASTER §2c

| ID | Item | Effort |
|----|------|--------|
| 2.16 | Publish performance feedback loop (YouTube Analytics → style learning) | L |
| 2.18 | Speaker diarization (`pyannote.audio`) | L |
| 2.19 | yt-dlp subtitle reuse (skip Whisper when subs exist) | M |
| 2.21 | Live stream / OBS integration | L |
| 2.22 | Instagram Reels adapter | L |

---

### F6. Post-release code consolidation

**Source:** MASTER §FS-3 (deferred P2)

Presigned URL helper unification, thumbnail ffmpeg helper, OAuth adapter base, rate-limit boilerplate, tier limit enforcement, OpenAPI client regen, platform label maps — **nice-to-have refactors only**.

---

## Plan source index (Cursor)

| File | Built? | Section |
|------|--------|---------|
| `streamclip_stack_build_24bac5fb.plan.md` | ✅ | Completed |
| `streamclip_production_bring-up_670b78c3.plan.md` | ✅ | Completed |
| `streamclip_feature_roadmap_5bd3ae26.plan.md` | ✅ | Completed |
| `streamclip_product_packaging_a9e8ec9f.plan.md` | ✅ | Completed |
| `streamclip_ai_models_975144ab.plan.md` | ❌ | **Future F1–F5** |
| `streamclip_sagemaker_integration_4894fa37.plan.md` | ❌ | **Future F3** |

Plans live under `C:\Users\locat\.cursor\plans\` (or workspace `.cursor/plans/`).

---

## Agent sync checklist

When closing **active-track** work:

1. Update [`docs/MASTER_TODO.md`](docs/MASTER_TODO.md) row status.
2. Update **this file** (`PLAN.md`) task status (⬜ → ✅).
3. Update [`docs/BETA_TESTER_PLAN.md`](docs/BETA_TESTER_PLAN.md) if a phase gate moves.
4. **Do not** mark Future updates (F*) complete until unlock condition is met.

When the active track completes:

1. Add an **Unlock record** below with date + sign-off.
2. Move F1 into Active track (recommended first future slice: LLM router only).
3. Re-run gap analysis skill before starting F3 (SageMaker spend).

---

## Unlock record

| Date | Sign-off | Notes |
|------|----------|-------|
| — | — | Future updates remain **frozen** |

---

### Immediate next action (active track)

1. **Ops / on-call:** H+0…H+72 monitoring per [`docs/BETA_GO_LIVE.md`](docs/BETA_GO_LIVE.md) §7 — triage tester bugs; confirm ≥3 T0-1 by H+2.
2. **Team:** Drive Phase 0 cohort T0-1..T0-4 completion → P0-6 / MASTER §8.16 exit (incl. staging LS purchase → activate).
3. **Ops (autonomous):** Keep `OPS_WEBHOOK_URL` + optional `STREAMCLIP_OBSERVABILITY__SENTRY_DSN` live — see [`docs/OPS_ALERTING.md`](docs/OPS_ALERTING.md). n8n removed.
