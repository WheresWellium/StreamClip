# StreamClip — Master TODO (Release Readiness)

**Living document — running list of everything left before packaging and distributing
StreamClip as a Windows desktop executable, with a macOS port to follow.**

Last updated: 2026-07-07 (MASTER consolidation + coverage truth §3.10) · Owner: core team  
Legend: 🔴 blocker · 🟡 important · 🟢 nice-to-have | Effort: S (<1d) M (1–3d) L (1w+)

**Desktop embedded runtime (ADR-001):** §4.1–4.11 ✅ · §4.10 installer scaffold ✅ (NSIS + signing docs) · §4.13 Electron ✅ · Next: EV cert + signed release (§4.10).

**Cross-refs:** [`docs/BETA_TESTER_PLAN.md`](BETA_TESTER_PLAN.md) · [`docs/BETA_GO_LIVE.md`](BETA_GO_LIVE.md) · [`docs/GAP_ANALYSIS.md`](GAP_ANALYSIS.md) · [`docs/ADR-001-desktop-packaging.md`](ADR-001-desktop-packaging.md)

---

## 1. Ship the current changeset (do first)

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 1.1 | ~~Commit the uncommitted diff~~ ✅ committed `7c32b2c` (temp scripts + coverage artifacts deleted, `.gitignore` tightened) | ✅ | — |
| 1.2 | ~~Run `alembic upgrade head`~~ ✅ through `0007_license_issuance` on dev stack. **Current head:** `0010_password_reset_tokens` — rerun `alembic upgrade head` on every deploy | 🟡 | S |
| 1.3 | ~~Fix anonymous-scope contract regression~~ ✅ `scope.py` now raises `StreamClipError(code="device_id_required")`; source validation moved before device upsert; test client sends `X-Device-Id` | ✅ | — |
| 1.4 | ~~Regenerate `web/lib/api/openapi.ts`~~ ✅ regenerated (`988aaac`); fixed `uploads.py` dependency that broke schema generation; `approval_status` now a literal union | ✅ | — |
| 1.5 | ~~Commit large in-flight diff~~ ✅ committed `be095a9` (276 files: desktop §4.1–4.7a + §4.13, trust-ops, coverage batches, docs) | ✅ | — |
| 1.6 | ~~Regenerate `web/lib/api/openapi.ts` after recent API surface changes~~ ✅ regenerated offline (no Docker); new paths: `/storage/{key}`, clip words, waveform, privacy settings, bug reports, license revoke; `CreateJobRequest` override extended for `profanity_filter`/`profanity_mode` | ✅ | — |

## 2. Incomplete features / stubs (full scaffold scan, 2026-07-01)

### 2a. Monetization chain

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 2.1 | ~~TikTok video upload stub~~ ✅ Content Posting API **inbox flow** implemented (`upload_video_file`: chunked upload + status polling); worker wired; UI explains the finish-in-app step; covered by `tests/test_tiktok_adapter.py`. **Remaining:** direct public posting needs `video.publish` scope + TikTok app audit; flag stays off until app approval | 🟡 | M |
| 2.2 | ~~Stripe billing stub~~ ✅ removed (`backend/api/billing.py` deleted, stub dropped from `core/billing.py`) — Lemon Squeezy is the sole provider | ✅ | — |
| 2.3 | ~~Lemon Squeezy webhook never persists keys~~ ✅ webhook fail-closed + signature verified + idempotent key persistence; LS-native `license_key_created` handled. ✅ `order_created` fallback now emails the key (`send_license_key_email` via dispatch seam, replay-guarded; `test_license_hardening.py`) | ✅ | — |
| 2.4 | ~~License activation accepts any well-formed key~~ ✅ activation now requires a commerce-issued key (DB allowlist), rejects revoked keys, enforces `max_activations` across machine rebinds (migration `0007_license_issuance`) | ✅ | — |
| 2.5 | ~~Pick ONE billing provider~~ ✅ Lemon Squeezy chosen; chain wired: purchase → webhook → persisted key → activation → entitlement JWT → tier. Covered by `tests/test_license_chain.py` | ✅ | — |
| 2.6 | ~~`COMMERCIAL.md` promises Instagram Reels~~ ✅ promise cut (moved to roadmap wording); Stripe-based Cloud tier removed from the doc. Adapter itself stays on the roadmap (§2.22) | ✅ | — |
| 2.7a | ~~Queued/scheduled publishes uneditable~~ ✅ `PATCH /api/distribution/publish-jobs/{id}` (title/description; reschedule for scheduled jobs) + inline edit form in the queue; guarded once upload starts (409) | ✅ | — |
| 2.8a | ~~Vault clips unrenamable~~ ✅ `PATCH /api/vault/clips/{id}` + inline rename in the vault grid | ✅ | — |

### 2b. Scaffolded-but-unwired

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 2.7 | ~~Asset vault unwired~~ ✅ end-to-end: overlay engine merges DB `Asset` rows with the filesystem manifest (`records_from_db_assets` in `core/overlay.py`, wired into `process_clip` with per-job download cache + failed-download degradation); `assetsApi` client methods + server actions; management UI at `/settings/assets` (upload GIF/PNG/MP4 via presigned PUT, semantic description, delete). Matcher re-indexes only when the asset set changes (GAP U15) | ✅ | — |
| 2.8 | ~~Webhook settings unwired~~ ✅ `WebhookPanel` form on the settings page (get/save/remove via server actions); `settingsApi.getWebhook`/`updateWebhook` added | ✅ | — |
| 2.9 | ~~Token refresh stub~~ ✅ BFF route `web/app/api/auth/refresh/route.ts` exchanges the httpOnly refresh cookie server-side and rotates both cookies; focus handler debounced to 5 min | ✅ | — |
| 2.10 | ~~`backend/cloud/tenant.py` multi-tenant stub~~ ✅ **Removed** (2026-07-09) — unwired stub + `docker-compose.cloud.yml` deleted; design notes remain in `docs/cloud-deploy.md` (design-stage only) | ✅ | — |
| 2.11 | ~~Onboarding wizard never calls onboarding-complete~~ ✅ `completeOnboardingAction` posts the device id server-side on finish | ✅ | — |
| 2.12 | ~~Splice UI always sends `transition: "cut"`~~ ✅ transition picker (hard cut / crossfade) in the merge toolbar | ✅ | — |
| 2.13 | ~~`lemon_squeezy_store_id` defined, never read~~ ✅ removed from config and `COMMERCIAL.md` | ✅ | — |
| 2.14 | ~~Duplicate job-scoped publish routes~~ ✅ single-clip route deprecated in OpenAPI (see 7.6); batch-publish intentionally stays job-scoped per GAP register | ✅ | — |
| 2.15 | ~~Create-job UI missing **`asset_pack_id`** and **`profanity_mode`** fields~~ ✅ censor-style select + overlay pack dropdown in More options; wired through zod schema and payload (GAP U25) | ✅ | — |

### 2c. Roadmap features (not started)

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 2.16 | Publish performance feedback loop — poll YouTube Analytics, feed style learning | 🟢 | L |
| 2.17 | ~~Multi-aspect export — all presets 9:16 only~~ ✅ curated catalog (9:16, 1:1, 4:5, 16:9, 2:3) in `core/creator_options.py`; reframe engine handles any target AR; job-level `aspect_ratio` + per-clip override; Premiere-style dropdown in create form + clip editor; splice guards mixed ARs | ✅ | — |
| 2.18 | Speaker diarization (`pyannote.audio` commented out in requirements) | 🟢 | L |
| 2.19 | yt-dlp subtitle reuse (`fetch_subs_on_long` downloads subs; Whisper always re-runs) | 🟢 | M |
| 2.20 | ~~UI design overhaul — "midnight terminal" system~~ ✅ midnight-green tokens + white hairline `--frame` border system, hard offset shadows, near-sharp radii; Space Grotesk (UI) + JetBrains Mono (labels/data); compact primitives (buttons h-8, inputs h-8, card p-4); help (?) icons removed — badges/labels/section headers now self-explain on hover; tooltips translucent (`bg-popover/70` + blur) | ✅ | — |
| 2.21 | Live stream / OBS integration (CREATOR_PLATFORM Later) | 🟢 | L |
| 2.22 | Instagram Reels adapter (CREATOR_PLATFORM, GAP_ANALYSIS deferral) | 🟢 | L |

### 2d. Verified fine (audit false alarms — no action)

- `core/export_bundle.py`, `core/splice.py` — implemented and tested
- `core/style_learning.py` — implemented + wired (GAP doc C9 "research" is stale)
- Per-clip webhooks — implemented (`pipeline_tasks.py:776+`; GAP C8 stale)

## 3. Test debt

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 3.1 | ~~Unit tests for `DistributionService`~~ ✅ `tests/test_distribution_service.py` | ✅ | — |
| 3.2 | ~~HTTP tests for `/api/distribution/*` and `/api/vault/*`~~ ✅ `tests/test_distribution_vault_http.py` | ✅ | — |
| 3.3 | ~~E2E publish flow (Playwright)~~ ✅ `web/e2e/happy-path.spec.ts` — 12/12 PASS with `E2E_RUN=1` (2026-07-09); **CI-required** via `e2e` job in `.github/workflows/test.yml` (`E2E_RUN=1`) | ✅ | M |
| 3.4 | ~~`test_score_parallel_and_ensemble` fails locally (missing `ollama`)~~ ✅ `_build_client` stubbed in test | ✅ | — |
| 3.5 | Coverage gate ratchet — **`fail_under=95`** (see §3.10). Last full Docker run: **95.91%** (2026-07-09) — **gate GREEN**. **110% plan:** 100% line + hot-path branches + Playwright smoke | 🟢 | L |
| 3.6 | ~~Zero-test surfaces~~ ✅ batches 1–3 + Playwright e2e (§3.3) | ✅ | — |
| 3.7 | **110% hot-path gaps** — see checklist below; branch measurement via `scripts/verify_branch_coverage.ps1` (Phase 0 informational; `-FailUnderBranch 85` PASS 2026-07-09) | 🟡 | M |
| 3.8 | ~~**`verify_stack.ps1` on clean Windows 11 VM**~~ ✅ 2026-07-09 clean-slate Docker wipe (`down -v` → rebuild → verify_stack + verify_coverage 95.02%); Hyper-V unavailable on operator host — see `BETA_GO_LIVE` §8 | ✅ | S |
| 3.9 | ~~Desktop verify scripts in CI or release checklist~~ ✅ `verify_desktop.ps1` in `.github/workflows/test.yml` (`desktop-smoke`) + `desktop-release.yml` pre-build | ✅ | S |
| 3.10 | **Coverage measurement (canonical)** — see subsection below | 🟡 | S |
| 3.11 | **CI coverage job** — ✅ `.github/workflows/test.yml` runs Docker pytest + `fail_under=95` on PR/`main` (fails until §3.5 green) | 🟡 | S |

### 3.10 Coverage measurement (single source of truth)

**“110%” definition** (line coverage caps at 100%; stretch = line + branches + E2E):

| Pillar | Gate | Phase 0 (Docker beta) | Phase 1+ |
|--------|------|----------------------|----------|
| Line | `.coveragerc` `fail_under` | **95** (active) | **100** |
| Hot-path branches | ≥85% on listed modules | Waived | Required (`branch = True` in `.coveragerc` when ready) |
| E2E smoke | Playwright `E2E_RUN=1` | **CI-required** (`test.yml` `e2e`); local also via `verify_stack.ps1 -RunE2E` | Required |
| Stack verify | `verify_stack.ps1` | Required (tests default `--no-cov`; does **not** prove coverage %) | Required + `-WithCoverage` before invites |

**Current measured line coverage (2026-07-27):** **96%** (372 miss / 10358; `verify_coverage.ps1 -SkipBuild`) — **gate GREEN**.

**110% progress (estimated composite ~91/110):**

| Pillar | Target | Current | Remaining |
|--------|--------|---------|-----------|
| Line | 100% (Phase 1+) | **96%** (2026-07-27 SkipBuild) | 372 stmts |
| Hot-path branches | ≥85% | **~87%** on §3.7 modules via `verify_branch_coverage.ps1` | Phase 1: enforce `-FailUnderBranch 85` |
| E2E smoke | §3.3 | health/jobs/create/list + distribution auth checks | OAuth E2E deferred |
| Clean VM | §3.8 | `docs/CLEAN_VM_VERIFY.md` | **PASS 2026-07-09** clean-slate Docker (`down -v`); Hyper-V N/A |

**§3.7 hot-path line checklist (404 total miss; priority order):**

| Module | Cover | Miss | Status |
|--------|-------|------|--------|
| `core/tasks/pipeline_tasks.py` | 100% | 0 | 🟢 H3 DONE — `tests/test_pipeline_tasks_h3_coverage.py` (see `tmp/h3-pipeline-coverage-status.md`) |
| `backend/services/sse.py` | 96%+ | ≤9 | 🟢 most paths covered (`test_coverage_hotpath_finish.py`) |
| `core/tasks/publish_tasks.py` | 98% | 4 | 🟢 |
| `backend/api/distribution.py` | 100% | 0 | 🟢 H1 DONE — line+branch; `tests/test_distribution_api_oauth.py` (sibling `1be7f1db`) |
| `backend/db/repositories.py` | 100% | 0 | 🟢 H2 DONE — `tests/test_repositories_coverage5.py`; gate still PASS 96% |
| `core/inprocess_worker.py` | 83% | 32 | 🟡 desktop — partial waiver in Docker scope |

**New test files (2026-07-07):** `test_coverage_hotpath_finish.py`, `test_coverage_tier_b_api.py`

**Scripts:** `verify_coverage.ps1` (line gate, parses pytest cov fail text), `verify_branch_coverage.ps1` (branch measure), `verify_stack.ps1 -WithCoverage` (aligned with line gate)

**Phase 0 invite rule:** `verify_stack.ps1` green **and** `verify_coverage.ps1` green (≥95% line). Stack-only verify is for local dev smoke, not beta clearance.

**Canonical command** (only percentage cited in docs):

```powershell
docker compose exec -T api pytest tests/ -m "not desktop" -q `
  --cov=backend --cov=core --cov-report=term-missing:skip-covered
```

Shortcut: `.\scripts\verify_coverage.ps1`

**Scope:** `backend` + `core` only (not `web/`, `desktop_sidecar/`, `apps/`). **Exclusions:** `@pytest.mark.desktop` + `tests/conftest.py` `pytest_ignore_collect` for sidecar/installer/SQLite/prod-compose-in-Docker.

**Hot-path branch targets (Phase 1+):** `core/tasks/pipeline_tasks.py`, `backend/services/sse.py`, `core/distribution/*`, `backend/services/job_service.py`.

**Footguns:**

- `pytest.ini` always adds `--cov` — **subset runs** (single file) enforce `fail_under` on partial scope → misleading low %.
- `verify_stack.ps1` default uses `--no-cov` (fast); use **`-WithCoverage`** for authoritative gate.
- `test_prod_compose.py` runs on **host only** (ignored when `/.dockerenv` exists).


## 4. Windows desktop packaging (.exe)

**Current state:** Electron shell at `apps/desktop` spawns `streamclip-sidecar.exe` (prod) or `python -m desktop_sidecar` (dev) — no Docker required. See `apps/desktop/src/main.ts` and `docs/ADR-001-desktop-packaging.md` for the embedded runtime architecture. §4.1–4.13 are ✅; remaining work is EV code-signing and the signed release (§4.10).

**Decision (4.0):** ✅ **Accepted 2026-07-07** — embedded runtime (SQLite + in-process queue + bundled Python sidecar, no Docker). Rationale: `docs/ADR-001-desktop-packaging.md`.

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 4.1 | **Database**: ✅ SQLite (aiosqlite) profile + portable Alembic migrations (`backend/db/types.py`, `config/desktop.yaml`) | 🟢 | M |
| 4.2 | **Task queue**: ✅ In-process worker (`core/inprocess_worker.py`, `core/task_runner.py`, memory progress bus). Enable via `STREAMCLIP_QUEUE__BACKEND=inprocess` or `config/desktop.yaml` | 🟢 | L |
| 4.3 | **Storage**: ✅ LocalStorage served via `/storage/{key}` (GET/PUT); Next.js rewrite proxies same-origin; `test_local_storage_http.py` | 🟢 | S |
| 4.4 | ~~LLM desktop defaults~~ ✅ `config/desktop.yaml` documents `STREAMCLIP_LLM__PROVIDER=openai|anthropic` + key env; shorter 30s timeout; no-LLM path degrades to score 0 (`core/virality.py:301`) with ensemble still ranking | ✅ | — |
| 4.5 | **ffmpeg**: ✅ `core/ffmpeg_bins.py` resolves bundled `bin/ffmpeg/` or PATH; all pipeline call sites use `ffmpeg_bin()` / `ffprobe_bin()` | 🟢 | S |
| 4.6 | **Python runtime**: ✅ **Full ML bundle** — spec collects torch (CPU wheels via `requirements-desktop.txt`), ctranslate2/faster-whisper, ultralytics (`module_collection_mode="py"`), mediapipe, librosa, celery/kombu submodules; excludes asyncpg/psycopg/boto3/sentry. Frozen root resolves via `sys._MEIPASS`; env config applied **before** backend import. ~1.1 GB one-dir; smoke-tested end-to-end (`verify_sidecar_exe.ps1`: boot → health → SQLite migrations). `STREAMCLIP_LITE=1` for API-only bundle. Weights download on first run (§4.8) | 🟢 | L |
| 4.7 | **Web UI**: ✅ Static export — `backend/static_ui.py`, `NEXT_STATIC_EXPORT=1` build, `build_desktop_ui.ps1`, client actions in `web/lib/api/actions/` | 🟢 | L |
| 4.8 | **First-run experience**: ✅ background model prefetch at sidecar boot (`core/model_prefetch.py` — whisper/YOLO/embedder, thread-safe status), `/api/health/models` progress endpoint, `ModelWarmupBanner` polling UI in layout. Data dir ✅ via §4.18. Opt-out: `STREAMCLIP_SIDECAR_SKIP_PREFETCH=1` | 🟢 | M |
| 4.9 | **Windows-isms audit**: ✅ swept core/backend — no `shell=True`/POSIX shells/symlinks/fork; concat list now POSIX paths + quote-escaped (`core/splice.py` + regression test); all text I/O explicit UTF-8 (url resolver meta, overlay manifest, transcript JSON); ASS filter escaping already handled. Verify script extended. Long paths: workspace uses UUID-keyed dirs (bounded) | 🟢 | M |
| 4.10 | **Installer**: ✅ NSIS via electron-builder — `build_desktop_installer.ps1`; `publish_desktop_release.ps1` uploads Setup + `latest.yml`; **`v1.0.0-beta.6` published** (unsigned). EV Authenticode runbook in `packaging/installer/RELEASE_CHECKLIST.md`. **Remaining:** purchase EV cert + first signed release | 🟡 | M |
| 4.11 | **GPU detection**: ✅ `core/gpu_profile.py` — CUDA + NVENC probes, safe fallbacks in `export_video`/`transcribe`, env defaults in desktop sidecar, `cuda`/`nvenc` in `/api/health/stack`. Config defaults remain CPU/libx264 | 🟢 | S |
| 4.12 | ~~Licensing UX~~ ✅ settings License panel wired to typed `licenseApi` client + `activateLicenseAction` with friendly error copy (invalid/revoked/limit), perpetual expiry display | ✅ | — |
| 4.13 | **Electron shell**: ✅ Spawns sidecar (`python -m desktop_sidecar` dev / bundled exe prod), BrowserWindow at `http://127.0.0.1:8765/`, preload IPC (start/stop/health), tray icon fallback, auto-updater stub | 🟢 | M |
| 4.14 | **Prod compose gaps**: ✅ `docker-compose.prod.yml` — distribution OAuth env on api/worker, `assets_data` volume + `seed_assets_if_empty.py`, CPU-safe worker defaults, configurable `STREAMCLIP_WORKER_QUEUES`, optional `gpu-worker` profile | 🟢 | S |
| 4.15 | **Alembic `upgrade head` on desktop sidecar startup** — ✅ in `desktop_sidecar/run.py` | 🟢 | S |
| 4.16 | **`scripts/verify_desktop.ps1`** — aggregate db + storage + ffmpeg smoke (inprocess optional via `verify_inprocess.ps1`) | 🟢 | S |
| 4.17 | **Full in-process parity**: ✅ all direct Celery `.delay()` / `send_task` (distribution, commerce, support, vault, CLI) routed through `core/task_dispatch.py` / `task_runner`; in-process Beat loop fires scheduled publishes + cleanup (`queue.inprocess_beat`, only while app runs — see BETA_KNOWN_ISSUES) | 🟢 | M |
| 4.7a | **Server Actions migration** — ✅ `web/lib/api/actions/*` + `client-session.ts`; components use client API; live progress BFFs under `web/app/api/.../progress/` (orphan `_api_bff/` removed) | 🟢 | L |
| 4.18 | **Production desktop config profile** — ✅ frozen builds (or `STREAMCLIP_DESKTOP_DATA_DIR`) resolve DB/storage/workspace/cache under `%LOCALAPPDATA%\StreamClip` (`~/.streamclip` fallback) via env overrides in `desktop_sidecar/run.py`; config file keeps dev defaults | 🟢 | S |

## 5. macOS port (after Windows)

**Scaffold (2026-07-08):** Darwin data dir (§5.4), arm64-first DMG naming (§5.5),
`scripts/build_desktop_installer_macos.sh` + `packaging/installer/MACOS.md`. §5.1
VideoToolbox encode path ✅ (code + tests; Darwin ffmpeg bundle still Mac-host).
Real DMG still needs a Mac host (§5.2–5.3).

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 5.1 | ~~ffmpeg with VideoToolbox hw accel~~ ✅ `core/gpu_profile.py` — `videotoolbox_available` + `effective_export_codec` prefers `h264_videotoolbox` on Darwin when NVENC N/A; `export_video` `-q:v` args; `libx264` ultimate fallback; tests mock `is_darwin` | ✅ | — |
| 5.2 | Torch on Apple Silicon (MPS) for YOLO; CTranslate2 arm64 wheels for whisper — CI scaffold: `desktop-release.yml` macOS job installs `requirements-desktop.txt`, `download_ffmpeg_macos.sh`, `build_desktop_ui.sh` (`continue-on-error` until green). Live MPS/CTranslate2 smoke still needs Mac host | 🟡 | M |
| 5.3 | App bundle (.app), codesigning + notarization, Gatekeeper — script + entitlements ready; Apple Developer + notarize secrets still external | 🔴 | M |
| 5.4 | Paths: `~/Library/Application Support/StreamClip`; no `%LOCALAPPDATA%` | 🟢 | S |
| 5.5 | arm64 Apple Silicon first; universal2 / x86_64 later (documented) | 🟢 | S |
| 5.6 | In-process worker from 4.2 is cross-platform ✅ (no Memurai/Redis broker required on desktop) | 🟢 | — |

## 6. Docs / env hygiene

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 6.1 | ~~TECHNICAL_DESIGN.md stale (social publish "out of scope")~~ ✅ updated to Rev 4 (2026-07-01) | ✅ | — |
| 6.2 | ~~GAP_ANALYSIS.md stale rows~~ ✅ C3/C8/C9 marked shipped with evidence; T47 fixed at the source | ✅ | — |
| 6.3 | ~~Desktop packaging ADR~~ ✅ `docs/ADR-001-desktop-packaging.md` — **Accepted 2026-07-07** | ✅ | — |
| 6.4 | ~~`.env.example` env-var mismatches~~ ✅ commerce vars renamed; rate-limit opt-out documented as dev-only | ✅ | — |
| 6.5 | ~~README + CREATOR_PLATFORM.md stale~~ ✅ refreshed 2026-07-07 (layout §6.7, CREATOR_PLATFORM §6.10; GAP T54 closed) | ✅ | — |
| 6.6 | ~~`docs/cloud-deploy.md` aspirational~~ ✅ design-stage banner added (keep-or-delete per 2.10) | ✅ | — |
| 6.7 | ~~README project layout~~ ✅ layout refreshed: `core/ingest/`, router list, migrations `0001`–`0009`, desktop paths (`desktop_sidecar/`, `packaging/`, `static/ui/`, `bin/ffmpeg/`, `config/desktop.yaml`) | ✅ | — |
| 6.8 | ~~GPU queue narrative~~ ✅ `worker` queues now `${STREAMCLIP_WORKER_QUEUES:-default,gpu}` — set `default` with `--profile gpu` for true isolation; README ship checklist updated (GAP T56) | ✅ | — |
| 6.9 | ~~Reframe `auto` preset~~ ✅ README table already says "clip emotion heuristics"; TDD has no LLM-picks wording (GAP T57 stale) | ✅ | — |
| 6.10 | ~~`CREATOR_PLATFORM.md` sync~~ ✅ asset vault end-to-end + desktop §4.1–4.5 marked shipped; Next section updated to §4.6–4.13 | ✅ | — |
| 6.11 | ~~`.cursor/skills/streamclip-development/SKILL.md`~~ ✅ desktop profile section added (SQLite, inprocess queue, sidecar, static UI, verify scripts) | ✅ | — |
| 6.12 | ~~`docs/BETA_TESTER_PLAN.md` §2~~ ✅ hard blocker 4.0 marked accepted 2026-07-07 | ✅ | — |
| 6.13 | ~~**External product UI posture**~~ ✅ `NEXT_PUBLIC_DEV_TOOLS`; API/OpenAPI removed from shipped UI; operator Advanced gated; beta docs app-first copy (`BETA_TESTER_QUICKSTART`, tutorials) | ✅ | S |
| 6.14 | ~~**Redeploy public MkDocs on Vercel**~~ ✅ 2026-07-18 — `streamclip-henna.vercel.app` (Architecture/Operations nav trimmed) | ✅ | S |

## 7. Cleanup

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 7.1 | ~~Delete stray artifacts~~ ✅ verified clean 2026-07-02 | ✅ | — |
| 7.2 | ~~`backend/api/vault.py` excessive blank lines~~ ✅ reformatted | ✅ | — |
| 7.3 | ~~Narrow Celery `autoretry_for=(Exception,)` in `publish_tasks.py`~~ ✅ | ✅ | — |
| 7.4 | ~~YouTube upload loads full file into memory~~ ✅ streams in 8 MB chunks | ✅ | — |
| 7.5 | ~~Destinations drawer default tab~~ ✅ now defaults to `"publish"` | ✅ | — |
| 7.6 | ~~Deprecate `POST /api/jobs/{id}/clips/{clip_id}/publish`~~ ✅ OpenAPI deprecated + pointer to `/api/distribution/publish` | ✅ | — |

## 8. Beta tester program (gated on 110% coverage)

**Canonical plan:** [`docs/BETA_TESTER_PLAN.md`](BETA_TESTER_PLAN.md) — Phase 0 (Docker
technical) → Phase 1 (creator closed, GHCR/hosted) → Phase 2 (desktop `.exe`).

**Phase 0 status (2026-07-09):** **Invites SENT.** Engineering invite gate was CLEARED earlier (coverage + clean-slate). Now in **H+0 monitoring** (`BETA_GO_LIVE` §7). Phase 0 **exit** still needs tester T0 results (§8.16). Full **110%** row (§3.10) required before Phase 1.

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 8.1 | Hit 110% coverage gate (§3.5 → 100% line + §3.7 branches + §3.3 Playwright) — Phase 1+ blocker | 🔴 | L |
| 8.2 | ~~Write `docs/BETA_TESTER_QUICKSTART.md` at Phase 0 open~~ ✅ exists | ✅ | S |
| 8.3 | Phase 0 cohort (5–10): Docker self-host, T0 flows in beta plan §4.3 | 🟡 | M |
| 8.4 | Phase 1: 20–40 creators + optional GHCR tags (license email §2.3 ✅) | 🟡 | M |
| 8.5 | Phase 2: desktop closed beta (§4.6–4.8 minimum) — 50–100 testers | 🔴 | L |
| 8.6 | ~~Align commerce docs/code to one-time purchase~~ ✅ `COMMERCIAL.md` + operator checklist in `BETA_OPS_PHASE0` §6 (one-time SKU, webhook URL, env secrets, optional variant IDs). **Remaining:** operator confirms live LS dashboard against that checklist | 🟢 | S |
| 8.7 | **`docs/BETA_KNOWN_ISSUES.md`** — keep current for TikTok inbox-only, no Instagram, CPU SLAs, SmartScreen unsigned desktop | 🟢 | S |
| 8.8 | ~~**GHCR image build + publish workflow**~~ ✅ 2026-07-09 — `images.yml` + `STREAMCLIP_IMAGE_PREFIX` in `docker-compose.prod.yml`; first-publish commands in `deploy/PRODUCTION.md` §8 (operator still runs first tag/dispatch) | ✅ | S |
| 8.9 | **Beta kit prep** — `scripts/prepare_beta_kit.ps1` → `dist/streamclip-beta-kit-*.zip` (quickstart, env examples, verify scripts, compose) | 🟢 | S |
| 8.10 | ~~Flip `docs/BETA_TESTER_PLAN.md` Draft → Active~~ ✅ plan doc **Active** 2026-07-07 (≠ beta invites open — see §3.5) | ✅ | S |
| 8.11 | ~~**Feedback channel**~~ ✅ 2026-07-09 — GitHub issue template `.github/ISSUE_TEMPLATE/beta-bug.yml` (job id, GPU, logs, steps) + `BETA_OPS_PHASE0` §1; Discord optional | ✅ | S |
| 8.12 | ~~**On-call rotation**~~ ✅ 2026-07-09 — `docs/BETA_ON_CALL.md` Phase 0 runbook (TBD role slots, severity matrix, first-72h checklist); operator fills names before invite | ✅ | S |
| 8.13 | ~~**OAuth redirect URIs**~~ ✅ 2026-07-09 — copy-paste checklist in `docs/distribution-runbook.md` (`youtube_shorts` / `tiktok` + `WEB_ORIGIN`) | ✅ | S |
| 8.14 | ~~**Quickstart fresh-reader review**~~ ✅ 2026-07-09 — Steps 1–4 + `verify_stack.ps1` PASS; published quickstart/download 200; fixed `SCBETA`→`SCPRO` key format + stale “exe not built” message; recorded in `BETA_INVITE_PACK.md` §2 | ✅ | S |
| 8.15 | ~~**Invite comms**~~ ✅ 2026-07-09 — operator confirmed Phase 0 invites sent; pack tooling in `prepare_invite_pack.ps1` / `BETA_INVITE_PACK.md` | ✅ | S |
| 8.16 | **Phase exit — Phase 0** (`BETA_TESTER_PLAN` §4.5): ≥4/5 complete T0-1..T0-4; no 🔴 >7d; LS test purchase → activate; 110% before Phase 1 — fill [`BETA_COHORT_EXIT.md`](BETA_COHORT_EXIT.md) then sync `BETA_GO_LIVE` §7–§8 | 🟡 | M |
| 8.17 | **Phase exit — Phase 1** (§5.6): ≥70% T1-1..T1-3; Playwright CI green (§3.3); GPU perf within `PERFORMANCE.md` (+25% beta tolerance) | 🟡 | M |
| 8.18 | **Phase exit — Phase 2** (§6.4): crash-free >98% (7d); install→first clip <45m median; signing (§4.10); macOS scoped (§5) | 🔴 | L |
| 8.19 | **Week-before-invite checklist** (`BETA_TESTER_PLAN` §8): **§3.5 green ✅** · **§3.8 clean-slate ✅ (2026-07-09)** · changelog/known issues · LS E2E purchase · **OAuth URIs (§8.13) ✅** · **Beat/scheduled-publish docs ✅** (`distribution-runbook` + quickstart/ops cross-links) | 🟡 | M |

## 9. Self-host / ops (Docker path — parallel to desktop)

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 9.1 | **`/api/health/stack` deep probe** — Docker operators only; beta users use **Settings → Get started** (Ready / Needs attention). Documented in `BETA_TESTER_QUICKSTART.md` §4 | 🟢 | S |
| 9.2 | **Prometheus/Grafana or log tail procedure** for opt-in beta testers — ✅ [BETA_OBSERVABILITY.md](BETA_OBSERVABILITY.md) covers health, `/metrics`, log-tail, critical beta signals, and opt-in log bundles; linked from `BETA_GO_LIVE` §3 / ops runbook | 🟢 | S |
| 9.3 | **MkDocs internal docs site** — maintain `mkdocs.yml`, Vercel deploy, keep `GAP_ANALYSIS` / `MASTER_TODO` in `exclude_docs` (`docs/INTERNAL.md`) | 🟢 | S |

## 10. Final Stretch — release readiness (2026-07-07)

**Source:** 7-way parallel `streamclip-gap-analysis` audit (backend/auth/billing, core pipeline, distribution/vault/ops, web frontend, desktop/deploy, media-serving, upload). All P0s and P1s resolved in the same session. Coverage gate held at **95.02%** (886 tests, 0 failures) throughout.

---

### FS-1 — Completed this session ✅

| # | What was fixed | Files changed |
|---|----------------|---------------|
| FS-1.1 | ~~Upload broken — MinIO had no CORS policy, blocked browser presigned PUT~~ ✅ `MINIO_API_CORS_ALLOW_ORIGIN: "*"` in dev compose; verified live (PUT 200, job created); 41/41 upload tests pass | `docker-compose.yml` |
| FS-1.2 | ~~Playback/thumbnails/download in prod — URLs fell back to unreachable `minio:9000`~~ ✅ `STREAMCLIP_STORAGE__PUBLIC_BASE_URL` (env-driven) added to `docker-compose.prod.yml` (api+worker) and dev worker/gpu-worker; `.env.production.example` documented | `docker-compose.yml`, `docker-compose.prod.yml`, `.env.production.example` |
| FS-1.3 | ~~No frontend URL refresh on presigned 1h expiry~~ ✅ `clip-card.tsx`/`clip-editor.tsx` hold local URL state; `onError` calls `refreshClipMediaAction` (refetches job) and retries once; download HEAD-checks before navigating; `useToastSafe` on final failure | `web/components/clips/clip-card.tsx`, `clip-editor.tsx`, `web/lib/api/actions/jobs.ts` |
| FS-1.4 | ~~Distribution/OAuth broken in dev compose — no `TOKEN_ENCRYPTION_KEY`~~ ✅ Fernet key + `WEB_ORIGIN` added to all dev services; verified live; `.env.example` + `distribution-runbook.md` updated | `docker-compose.yml`, `.env.example`, `docs/distribution-runbook.md` |
| FS-1.5 | ~~Prod worker never consumed `gpu` queue~~ ✅ default changed to `${STREAMCLIP_WORKER_QUEUES:-default,gpu}`; GPU-isolation override documented | `docker-compose.prod.yml`, `deploy/PRODUCTION.md` |
| FS-1.6 | ~~Race condition — global `cfg` mutated under parallel `process_clip`~~ ✅ `_apply_job_config`/`_apply_clip_overrides`/`_apply_aspect_ratio` take explicit `cfg_obj`; `process_clip` creates `local_cfg = cfg.model_copy(deep=True)` per invocation; regression test added; 64-test suite + 95.02% coverage pass | `core/tasks/pipeline_tasks.py`, `tests/test_aspect_ratio_pipeline.py` |
| FS-1.7 | ~~Tier quotas silently disabled — gated on `rate_limit.enabled`~~ ✅ quota block unconditional for authenticated users; Redis rate-limit path unchanged | `backend/services/job_service.py` |
| FS-1.8 | ~~`max_minutes_per_month` defined but never enforced~~ ✅ `QuotaExceededError` raised in `create_job` when limit exceeded; 0 = unlimited | `backend/services/job_service.py` |
| FS-1.9 | ~~License revoke didn't downgrade user tier or invalidate JWT~~ ✅ revoke downgrades `users.tier` → FREE when no other activated license remains; JWT blocklist limitation documented in `BETA_KNOWN_ISSUES.md` + `# TODO: jti blocklist` comment in `core/licensing.py` | `backend/api/admin.py`, `core/licensing.py`, `docs/BETA_KNOWN_ISSUES.md` |
| FS-1.10 | ~~Distribution unlocked before license activation~~ ✅ `_install_has_pro_license` now requires `status='activated'` | `backend/middleware/distribution.py` |
| FS-1.11 | ~~`/metrics` unauthenticated; default JWT secret active~~ ✅ `/metrics` gated by `STREAMCLIP_OBSERVABILITY__METRICS_API_KEY` (Bearer/header); loopback-only in non-dev otherwise; CRITICAL log on default JWT secret; documented in `deploy/PRODUCTION.md` + `.env.example` | `core/config.py`, `backend/api/metrics.py`, `backend/main.py`, `deploy/PRODUCTION.md`, `.env.example` |
| FS-1.12 | ~~Uploads presign endpoint had no ownership check~~ ✅ `GET /api/uploads/url` validates `uploads/` key prefix against requesting user/device; 403 on mismatch | `backend/api/uploads.py` |
| FS-1.13 | ~~Web UI ignored install-level Pro/Admin license for distribution~~ ✅ `hasDistributionAccessClient` no longer short-circuits on missing JWT; machine-license check always runs as fallback | `web/lib/distribution/client-access.ts`, `web/components/settings/distribution-section.tsx`, `web/lib/api/actions/distribution.ts` |
| FS-1.14 | ~~Header auth state stale after same-tab login~~ ✅ `setAuthTokens`/`clearAuthTokens` dispatch `"auth-changed"` event; `header-nav-wrapper.tsx` listens alongside `storage`/`focus` | `web/lib/auth/client-session.ts`, `web/components/layout/header-nav-wrapper.tsx` |
| FS-1.15 | ~~Publish SSE endpoint unroutable (`_api_bff/`)~~ ✅ job + publish-job progress BFFs moved to `web/app/api/.../progress/route.ts`; both visible in `npm run build` as `ƒ` dynamic routes; auth + `Last-Event-Id` forwarded | `web/app/api/distribution/publish-jobs/[id]/progress/route.ts` (new), `web/app/api/jobs/[id]/progress/route.ts` (new) |
| FS-1.16 | ~~Per-clip download didn't force-save cross-origin~~ ✅ `downloadBlob(url, filename)` utility created (fetch → blob → object URL → programmatic click); wire into `clip-card.tsx` after FS-1.3 review | `web/lib/utils/download.ts` (new) |
| FS-1.17 | ~~TikTok upload poll returned `"published"` on status-unknown timeout~~ ✅ poll returns `"pending"` on budget expiry; publish task releases claim to `"pending"` for retry | `core/distribution/tiktok.py`, `core/tasks/publish_tasks.py` |
| FS-1.18 | ~~`MASTER_TODO.md` §4 intro described Electron as Docker launcher (doc regression)~~ ✅ intro rewritten to describe embedded sidecar | `docs/MASTER_TODO.md` |
| FS-1.19 | ~~UX: `not-found.tsx` said "static desktop UI"~~ ✅ generic web 404 copy | `web/app/not-found.tsx` |
| FS-1.20 | ~~UX: Pro gate modal linked to `/settings` instead of license panel~~ ✅ links to `/settings?section=license` | `web/components/distribution/pro-gate-modal.tsx` |
| FS-1.21 | ~~UX: Distribution queue tabs missing a11y roles~~ ✅ `role="tablist"` / `role="tab"` / `aria-selected` added | `web/components/distribution/distribution-queue.tsx` |

---

### FS-2 — Still open (final push) 🟡

| # | Item | Effort | Who |
|---|------|--------|-----|
| ~~FS-2.1~~ ✅ | ~~**Wire `downloadBlob` into `clip-card.tsx`**~~ — import added; `onDownloadClick` now calls `downloadBlob(url, title+'.mp4')` after HEAD-check; fallback also uses `downloadBlob`; plain `<a>` replaced with `<button>` | S | Agent |
| ~~FS-2.2~~ ✅ | ~~**Wire `use-publish-progress.ts` into Distribution Queue UI**~~ — `PublishJobRow` sub-component extracted; calls `usePublishProgress(job.id)` for `publishing` rows; shows live progress bar + message; `router.refresh()` fires on SSE terminal event | M | Agent |
| ~~FS-2.3~~ ✅ | ~~**GHCR image prefix in `docker-compose.prod.yml`**~~ — all 5 `ghcr.io/streamclip/` image refs (api, worker ×3, web) replaced with `${STREAMCLIP_IMAGE_PREFIX:-ghcr.io/streamclip}/`; `.env.production.example` comment updated; `docker compose config --quiet` passes | S | Agent |
| ~~FS-2.4~~ ✅ | ~~**Clean-VM `verify_stack.ps1` run**~~ — 2026-07-09 clean-slate Docker (`down -v`); stack + coverage + branch≥85 PASS; recorded in `BETA_GO_LIVE` §8 | S | Agent |

---

### FS-3 — Deferred consolidation (post-release, P2) 🟢

| Area | Files | Target pattern |
|------|-------|----------------|
| Presigned URL generation | `job_service.to_dto`, `vault/service.py`, `uploads.py`, `jobs.py` | Single `storage.presign_for_browser(key)` helper |
| Thumbnail ffmpeg one-liner | `pipeline_tasks.py` (2 call sites) | Extract `extract_thumbnail()` helper |
| OAuth token exchange/refresh | `core/distribution/youtube.py`, `tiktok.py` | Shared `OAuthPlatformAdapter` base |
| Rate-limit dependency boilerplate | ~15 routers, ~50+ endpoints | Router-level `dependencies=[...]` instead of per-route |
| Tier limit checks | `vault/service.py` (correct) vs `assets.py`/`templates.py` (hardcoded) | Single `enforce_resource_limit()` via `get_tier_limits()` |
| API client types | `web/lib/api/client.ts` hand-written vs generated `openapi.ts` | Regenerate + import from OpenAPI per `CONTRIBUTING.md` |
| Platform label maps | 4 web components | Single shared `PLATFORM_LABELS` constant |
| Distribution context fetch | 3 web components/actions | Single shared helper |
| Monthly quota reset | `backend/db/repositories.py` | Beat task that zeroes `minutes_processed_this_month`/`jobs_used_this_month` on month rollover |

---

**Bottom line:** Phase 0 **invites are out** (2026-07-09). Monitor H+0…H+72 per `BETA_GO_LIVE` §7. Phase 0 exit = cohort T0 results (§8.16). Phase 1 still needs 110% coverage row.

---
## Plan sync checklist (agents)

**Consolidated index:** [`PLAN.md`](../PLAN.md) — active track (Beta Phase 0 → Phase 3) vs **Future updates (frozen)**.

When closing work from any plan doc, update **this file** and the source plan:

| Source | Update MASTER_TODO when… |
|--------|-------------------------|
| `PLAN.md` | Active-track or Future-unlock status changes |
| `GAP_ANALYSIS.md` | New T/U/C gap or deferral changes |
| `BETA_TESTER_PLAN.md` | Phase gates, kit contents, exit criteria |
| `BETA_GO_LIVE.md` | Launch checklist items move |
| `BETA_KNOWN_ISSUES.md` | Beta-facing limitation text changes |
| `TECHNICAL_DESIGN.md` §11 | Known limitations list changes |
| `ADR-001-desktop-packaging.md` | Desktop implementation order advances |
| `CREATOR_PLATFORM.md` | Roadmap Now/Next/Later shifts |

Invoke skill: **streamclip-gap-analysis** for full doc/code drift audits.


