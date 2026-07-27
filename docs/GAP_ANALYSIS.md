# qClip Gap Analysis

**Last run:** 2026-07-07 (revision 7 — MASTER consolidation + coverage truth)

## Executive summary

The **clip pipeline, distribution plane, and Phase 2–4 features are wired end-to-end**. The **95% line-coverage gate is the active target** (`fail_under=95` in `.coveragerc`); last full Docker suite reached **95.01%** — **gate GREEN** (2026-07-07). **Canonical measurement:** [`docs/MASTER_TODO.md`](MASTER_TODO.md) **§3.10**. Remaining stretch is **110%** (100% lines, hot-path branches, Playwright smoke) tracked in MASTER §3.5–§3.7, §8.1.

## Technical gaps

| ID | Claim | Status | Sev | Fix | Evidence |
|----|-------|--------|-----|-----|----------|
| T1–T52 | (prior revisions) | Mostly **Fixed** | — | — | See revision 4 |
| T53 | Coverage gate `fail_under=95` | **Done** | P1 | code | 95.01% Docker 2026-07-07; run `scripts/verify_coverage.ps1` to reconfirm |
| T54 | README project layout | **Fixed** | P2 | doc | MASTER §6.7 — layout refreshed |
| T55 | Export codec default | **Fixed** | P2 | code | `ExportConfig.codec` default `libx264` matches `config.yaml` / README (`core/config.py:135`) |
| T56 | GPU queue isolation | **Fixed** | P2 | code | `worker` queues now `${STREAMCLIP_WORKER_QUEUES:-default,gpu}`; set `default` with `--profile gpu` for isolation |
| T57 | Reframe `auto` preset | **Fixed** | P2 | doc | README preset table says "clip emotion heuristics"; matches `core/reframe.py` |
| T58 | Phase 2–4 backend features | **Fixed** | — | — | Profanity, words endpoint, waveform, `caption_words_per_group`, audio slate — verified in pipeline + API |
| T59 | License/commerce chain | **Fixed** | — | — | Lemon Squeezy webhook, email task, activation audit, admin revoke, perpetual JWT |
| T60 | `gpu-worker` volume parity | **Fixed** | P2 | both | `gpu-worker` mounts `./config:/app/config:ro` (`docker-compose.yml`) |
| T61 | CI coverage job | **Fixed** | P2 | code | `.github/workflows/test.yml` — MASTER §3.11 |

## UX gaps

| ID | Journey / control | Status | Sev | Fix | Evidence |
|----|-------------------|--------|-----|-----|----------|
| U1–U16 | (prior revisions) | Mostly **Fixed** | — | — | See revision 4 |
| U17 | Audio upload without feature gate | **Fixed** | P1 | code | `/api/meta` exposes `features.audio_ingest`; create form + `DirectUpload` restrict audio MIME when off |
| U18 | `ClipEditor` safe zones compile error | **Fixed** | P0 | code | `showSafeZones` state; `npm run typecheck` green |
| U19 | Words-per-group editor control | **Fixed** | P1 | code | Slider in Style section; saves `caption_words_per_group` |
| U20 | API docs in shipped app | **Removed** | P1 | code | OpenAPI/Swagger not in external UI; partners request privately; Docker dev may use `:8000/docs` with `STREAMCLIP_EXPOSE_API_DOCS=1` |
| U21 | `JobCard` nested `<button>` in `<Link>` | **Fixed** | P1 | code | Card uses `role="link"` + router; title edit stops propagation |
| U22 | Duplicate "Account" in header | **Fixed** | P2 | code | Settings vs Profile/Sign in labels in `header-nav.tsx` |
| U23 | SSE reconnect / `Last-Event-Id` | **Fixed** | P1 | code | `use-job-progress.ts` keeps EventSource on transient errors; polling after 20s fallback |
| U24 | SSE disconnect not surfaced | **Fixed** | P2 | code | `LiveProgress` amber banner for `reconnecting` / `polling` |
| U25 | `CreateJobRequest` fields not in form | **Fixed** | P2 | code | MASTER §2.15 — asset pack + profanity mode in create form |
| U26 | Save template omits profanity | **Fixed** | P2 | code | Template save/apply includes `profanity_filter` in `create-job-form.tsx` |
| U27 | Playwright full journey | Partial | P2 | defer | MASTER §3.3 — blocks 110% gate |
| U28 | Phase 3 UX (bug report, privacy, checklist) | **Fixed** | — | — | Wired in layout + settings hub |

## Modularity & duplication register

| Area | Finding | Severity | Recommendation |
|------|---------|----------|----------------|
| Publish routing | Job-scoped vs hub publish endpoints both delegate to `DistributionService` | P2 | Keep batch on jobs router; single-clip deprecated (MASTER §7.6) |
| `core/ingest.py` shim | Legacy re-export alongside `core/ingest/` package | P2 | README documents package; shim kept for imports |
| Coverage vs velocity | Prior notify/ingest modules under-tested | **Fixed** | Batches 5–6 + ratchet; see MASTER §3.10 |

## Creator-platform gaps (mastery trajectory)

| ID | Capability | Status | Priority |
|----|------------|--------|----------|
| C1–C9 | (prior) | **Shipped** | — |
| C10 | Timeline editor (waveform + trim + safe zones) | **Shipped** | — | `trim-timeline.tsx`, `safe-zone-overlay.tsx`, waveform API |
| C11 | Transcript word editor | **Shipped** | — | `transcript-edit-panel.tsx`, GET words |
| C12 | Profanity filter (job + captions) | **Shipped** | — | `core/profanity.py`, create-job checkbox |
| C13 | Audio-to-clip (v2 SKU) | **Shipped** | — | `audio_slate.py`, `features.audio_ingest` gate |

## 110% coverage gate (beta blocker)

**Authoritative definition:** [`docs/MASTER_TODO.md`](MASTER_TODO.md) **§3.10**.

| Milestone | Target | Current (2026-07-07) |
|-----------|--------|----------------------|
| Line coverage | `fail_under = 95` (Phase 0) / 100 (Phase 1+) | **95.01%** — gate GREEN (2026-07-07) |
| Hot-path branches | ≥85% on pipeline_tasks, sse, distribution, job_service | Not measured (`branch = True` commented in `.coveragerc`) |
| Playwright smoke | `E2E_RUN=1` happy path | Scaffold exists; optional in Phase 0 |
| Web build | `npx next build` | **Green** |

See `docs/BETA_GO_LIVE.md`, `docs/BETA_TESTER_PLAN.md` §1.

## Resolved since revision 6 (2026-07-07)

- T54 — README layout (MASTER §6.7)
- U25 — Create-job asset pack + profanity mode (MASTER §2.15)
- Distribution test debt — `tests/test_distribution_service.py`, `tests/test_distribution_vault_http.py`, OAuth helpers
- Coverage truth — MASTER §3.10, `scripts/verify_coverage.ps1`, `verify_stack.ps1 -WithCoverage`, CI `test.yml`

## Intentional deferrals (roadmap)

Tracked in **MASTER §2c** and §3:

- Speaker diarization (§2.18)
- Instagram Reels adapter (§2.22)
- TikTok direct publish (§2.1 remaining)
- Full Playwright upload → clips e2e (§3.3)
- yt-dlp subtitle reuse (§2.19)
- Hot-path branch coverage + ratchet to 100% line (§3.5–§3.7)

## Verification commands

```powershell
# Authoritative coverage (MASTER §3.10)
.\scripts\verify_coverage.ps1

# Fast stack + tests (no cov)
.\scripts\verify_stack.ps1

# Pre-invite gate
.\scripts\verify_stack.ps1 -WithCoverage
```

```bash
cd web && npm run typecheck && npx next build
docker compose exec -T api python -c "from backend.main import app"
```

## How to re-run

Invoke skill: **`streamclip-gap-analysis`** (`.cursor/skills/streamclip-gap-analysis/SKILL.md`)

See also: `docs/PERFORMANCE.md`, `docs/TECHNICAL_DESIGN.md`, `docs/BETA_GO_LIVE.md`, `docs/MASTER_TODO.md`
