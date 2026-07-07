# StreamClip Gap Analysis

**Last run:** 2026-07-06 (revision 6 — main gaps closed)

## Executive summary

The **clip pipeline, distribution plane, and Phase 2–4 features are wired end-to-end**. The **95% line-coverage gate is green** again (95.06%). P0/P1 UX blockers from the gap pass are resolved: `ClipEditor` compiles, SSE reconnect preserves `Last-Event-Id`, audio ingest is meta-gated, template profanity round-trips, and header nav is deduplicated. Remaining work is **110% stretch** (100% lines, hot-path branches, Playwright smoke) plus **doc polish** (README layout, GPU queue narrative).

## Technical gaps

| ID | Claim | Status | Sev | Fix | Evidence |
|----|-------|--------|-----|-----|----------|
| T1–T52 | (prior revisions) | Mostly **Fixed** | — | — | See revision 4 |
| T53 | Coverage gate `fail_under=95` | **Fixed** | P1 | code | Full suite 2026-07-06: **95.06%**; `notify_tasks`, `transcript_io`, `subtitle_import` at 100% |
| T54 | README project layout | **Stale** | P2 | doc | README lists `core/ingest.py` + 4 API modules + migration `0001` only; repo has `core/ingest/` package (8 modules), 14 routers, migrations `0001`–`0009` |
| T55 | Export codec default | **Fixed** | P2 | code | `ExportConfig.codec` default `libx264` matches `config.yaml` / README (`core/config.py:135`) |
| T56 | GPU queue isolation | **Fixed** | P2 | code | `worker` queues now `${STREAMCLIP_WORKER_QUEUES:-default,gpu}`; set `default` with `--profile gpu` for isolation |
| T57 | Reframe `auto` preset | **Fixed** | P2 | doc | README preset table says "clip emotion heuristics"; matches `core/reframe.py` |
| T58 | Phase 2–4 backend features | **Fixed** | — | — | Profanity, words endpoint, waveform, `caption_words_per_group`, audio slate — verified in pipeline + API |
| T59 | License/commerce chain | **Fixed** | — | — | Lemon Squeezy webhook, email task, activation audit, admin revoke, perpetual JWT |
| T60 | `gpu-worker` volume parity | **Fixed** | P2 | both | `gpu-worker` mounts `./config:/app/config:ro` (`docker-compose.yml`) |

## UX gaps

| ID | Journey / control | Status | Sev | Fix | Evidence |
|----|-------------------|--------|-----|-----|----------|
| U1–U16 | (prior revisions) | Mostly **Fixed** | — | — | See revision 4 |
| U17 | Audio upload without feature gate | **Fixed** | P1 | code | `/api/meta` exposes `features.audio_ingest`; create form + `DirectUpload` restrict audio MIME when off |
| U18 | `ClipEditor` safe zones compile error | **Fixed** | P0 | code | `showSafeZones` state; `npm run typecheck` green |
| U19 | Words-per-group editor control | **Fixed** | P1 | code | Slider in Style section; saves `caption_words_per_group` |
| U20 | API docs nav | **Fixed** | P1 | code | Header link to `/docs` (FastAPI OpenAPI UI) |
| U21 | `JobCard` nested `<button>` in `<Link>` | **Fixed** | P1 | code | Card uses `role="link"` + router; title edit stops propagation |
| U22 | Duplicate "Account" in header | **Fixed** | P2 | code | Settings vs Profile/Sign in labels in `header-nav.tsx` |
| U23 | SSE reconnect / `Last-Event-Id` | **Fixed** | P1 | code | `use-job-progress.ts` keeps EventSource on transient errors; polling after 20s fallback |
| U24 | SSE disconnect not surfaced | **Fixed** | P2 | code | `LiveProgress` amber banner for `reconnecting` / `polling` |
| U25 | `CreateJobRequest` fields not in form | Partial | P2 | defer | `asset_pack_id`, `profanity_mode` have no UI mapping |
| U26 | Save template omits profanity | **Fixed** | P2 | code | Template save/apply includes `profanity_filter` in `create-job-form.tsx` |
| U27 | Playwright full journey | Partial | P2 | defer | `E2E_RUN=1` smoke not green — blocks 110% gate |
| U28 | Phase 3 UX (bug report, privacy, checklist) | **Fixed** | — | — | Wired in layout + settings hub |

## Modularity & duplication register

| Area | Finding | Severity | Recommendation |
|------|---------|----------|----------------|
| Publish routing | Job-scoped vs hub publish endpoints both delegate to `DistributionService` | P2 | Keep batch on jobs router; deprecate single-clip jobs publish when safe |
| `core/ingest.py` shim | Legacy re-export alongside `core/ingest/` package | P2 | README should document package; shim kept for imports |
| Coverage vs velocity | Prior notify/ingest modules under-tested | **Fixed** | Batch 5–6 tests + notify/transcript/ingest gaps; ratchet toward 100% next |

## Creator-platform gaps (mastery trajectory)

| ID | Capability | Status | Priority |
|----|------------|--------|----------|
| C1–C9 | (prior) | **Shipped** | — |
| C10 | Timeline editor (waveform + trim + safe zones) | **Shipped** | — | `trim-timeline.tsx`, `safe-zone-overlay.tsx`, waveform API |
| C11 | Transcript word editor | **Shipped** | — | `transcript-edit-panel.tsx`, GET words |
| C12 | Profanity filter (job + captions) | **Shipped** | — | `core/profanity.py`, create-job checkbox |
| C13 | Audio-to-clip (v2 SKU) | **Shipped** | — | `audio_slate.py`, `features.audio_ingest` gate |

## 110% coverage gate (beta blocker)

| Milestone | Target | Current (2026-07-06) |
|-----------|--------|----------------------|
| Line coverage | `fail_under = 100` (stretch) / **95** (active) | **95.06%** — active gate **green** |
| Hot-path branches | ≥85% on pipeline_tasks, sse, distribution, job_service | Not verified |
| Playwright smoke | `E2E_RUN=1` happy path | Not started |
| Web build | `npx next build` | **Green** |

See `docs/BETA_GO_LIVE.md`, `docs/BETA_TESTER_PLAN.md` §1.

## Resolved since revision 5 (2026-07-06)

- T53 — Coverage gate restored via batch 5–6 tests (`notify_tasks`, `transcript_io`, `ingest/service`, `virality`, `transcribe`, `subtitle_import`, `twitch_chat`)
- T55 — Export codec Pydantic default aligned to `libx264`
- T60 — `gpu-worker` `./config` mount
- U22–U24 — Header nav, SSE reconnect UX, disconnect banner
- U26 — Template profanity save/restore
- Test fix — audio ingest gate tested at `UploadService.init_upload` (not `create_job`)

## Intentional deferrals (roadmap)

- Speaker diarization
- Instagram Reels adapter
- TikTok live upload (flag-gated)
- Full Playwright upload → clips e2e
- yt-dlp subtitle reuse for Whisper
- Deprecate job-scoped single-clip publish endpoint
- Asset vault dedicated management page (API exists; `/settings/assets` partial)
- README full layout refresh
- `asset_pack_id` / `profanity_mode` create-job form fields
- Hot-path branch coverage measurement + ratchet to 100% line coverage

## Verification commands

```bash
docker compose exec -T api python -m pytest tests/ -q --cov=backend --cov=core
cd web && npm run typecheck && npx next build
docker compose exec -T api python -c "from backend.main import app"
powershell -File scripts/verify_stack.ps1
```

## How to re-run

Invoke skill: **`streamclip-gap-analysis`** (`.cursor/skills/streamclip-gap-analysis/SKILL.md`)

See also: `docs/PERFORMANCE.md`, `docs/TECHNICAL_DESIGN.md`, `docs/BETA_GO_LIVE.md`
