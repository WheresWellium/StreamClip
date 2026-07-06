# StreamClip — Master TODO (Release Readiness)

**Living document — running list of everything left before packaging and distributing
StreamClip as a Windows desktop executable, with a macOS port to follow.**

Last updated: 2026-07-05 (coverage push: 79% → 82.7%, gate 82) · Owner: core team
Legend: 🔴 blocker · 🟡 important · 🟢 nice-to-have | Effort: S (<1d) M (1–3d) L (1w+)

---

## 1. Ship the current changeset (do first)

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 1.1 | ~~Commit the uncommitted diff~~ ✅ committed `7c32b2c` (temp scripts + coverage artifacts deleted, `.gitignore` tightened) | ✅ | — |
| 1.2 | ~~Run `alembic upgrade head`~~ ✅ dev stack at `0007_license_issuance`. Rerun on any other deploy | ✅ | — |
| 1.3 | ~~Fix anonymous-scope contract regression~~ ✅ `scope.py` now raises `StreamClipError(code="device_id_required")`; source validation moved before device upsert; test client sends `X-Device-Id` | ✅ | — |
| 1.4 | ~~Regenerate `web/lib/api/openapi.ts`~~ ✅ regenerated (`988aaac`); fixed `uploads.py` dependency that broke schema generation; `approval_status` now a literal union | ✅ | — |

## 2. Incomplete features / stubs (full scaffold scan, 2026-07-01)

### 2a. Monetization chain — broken end-to-end 🔴

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 2.1 | ~~TikTok video upload stub~~ ✅ Content Posting API **inbox flow** implemented (`upload_video_file`: chunked upload + status polling); worker wired; UI explains the finish-in-app step; covered by `tests/test_tiktok_adapter.py`. **Remaining:** direct public posting needs `video.publish` scope + TikTok app audit; flag stays off until app approval | 🟡 | M |
| 2.2 | ~~Stripe billing stub~~ ✅ removed (`backend/api/billing.py` deleted, stub dropped from `core/billing.py`) — Lemon Squeezy is the sole provider | ✅ | — |
| 2.3 | ~~Lemon Squeezy webhook never persists keys~~ ✅ webhook now fail-closed on missing secret, verifies signature, persists issued keys idempotently (`install_licenses.status="issued"`, order id + email recorded); handles LS-native `license_key_created` events. **Remaining:** automated key delivery email for the `order_created` fallback path (key currently surfaced once in webhook response / LS log) | 🟡 | S |
| 2.4 | ~~License activation accepts any well-formed key~~ ✅ activation now requires a commerce-issued key (DB allowlist), rejects revoked keys, enforces `max_activations` across machine rebinds (migration `0007_license_issuance`) | ✅ | — |
| 2.5 | ~~Pick ONE billing provider~~ ✅ Lemon Squeezy chosen; chain wired: purchase → webhook → persisted key → activation → entitlement JWT → tier. Covered by `tests/test_license_chain.py` | ✅ | — |
| 2.6 | ~~`COMMERCIAL.md` promises Instagram Reels~~ ✅ promise cut (moved to roadmap wording); Stripe-based Cloud tier removed from the doc. Adapter itself stays on the roadmap (2.18) | ✅ | — |
| 2.19 | ~~Queued/scheduled publishes uneditable~~ ✅ `PATCH /api/distribution/publish-jobs/{id}` (title/description; reschedule for scheduled jobs) + inline edit form in the queue; guarded once upload starts (409) | ✅ | — |
| 2.20 | ~~Vault clips unrenamable~~ ✅ `PATCH /api/vault/clips/{id}` + inline rename in the vault grid | ✅ | — |

### 2b. Scaffolded-but-unwired

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 2.7 | ~~Asset vault unwired~~ ✅ end-to-end: overlay engine merges DB `Asset` rows with the filesystem manifest (`records_from_db_assets` in `core/overlay.py`, wired into `process_clip` with per-job download cache + failed-download degradation); `assetsApi` client methods + server actions; management UI at `/settings/assets` (upload GIF/PNG/MP4 via presigned PUT, semantic description, delete). Matcher re-indexes only when the asset set changes (GAP U15) | ✅ | — |
| 2.8 | ~~Webhook settings unwired~~ ✅ `WebhookPanel` form on the settings page (get/save/remove via server actions); `settingsApi.getWebhook`/`updateWebhook` added | ✅ | — |
| 2.9 | ~~Token refresh stub~~ ✅ BFF route `web/app/api/auth/refresh/route.ts` exchanges the httpOnly refresh cookie server-side and rotates both cookies; focus handler debounced to 5 min | ✅ | — |
| 2.10 | `backend/cloud/tenant.py` multi-tenant stub — not imported anywhere; `docker-compose.cloud.yml` sets `STREAMCLIP_CLOUD_MODE`/`STRIPE_*` that **no code reads**. Remove or finish | 🟡 | L |
| 2.11 | ~~Onboarding wizard never calls onboarding-complete~~ ✅ `completeOnboardingAction` posts the device id server-side on finish | ✅ | — |
| 2.12 | ~~Splice UI always sends `transition: "cut"`~~ ✅ transition picker (hard cut / crossfade) in the merge toolbar | ✅ | — |
| 2.13 | ~~`lemon_squeezy_store_id` defined, never read~~ ✅ removed from config and `COMMERCIAL.md` | ✅ | — |
| 2.14 | ~~License panel placeholder shows `STREAMCLIP-XXXX`~~ ✅ placeholder now `SCPRO-XXXX-XXXX-XXXX-XXXX` | ✅ | — |
| 2.15 | ~~Duplicate job-scoped publish routes~~ ✅ single-clip route deprecated in OpenAPI (see 7.6); batch-publish intentionally stays job-scoped per GAP register | ✅ | — |

### 2c. Roadmap features (not started)

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 2.16 | Publish performance feedback loop — poll YouTube Analytics, feed style learning | 🟢 | L |
| 2.17 | ~~Multi-aspect export — all presets 9:16 only~~ ✅ curated catalog (9:16, 1:1, 4:5, 16:9, 2:3) in `core/creator_options.py`; reframe engine handles any target AR; job-level `aspect_ratio` + per-clip override; Premiere-style dropdown in create form + clip editor; splice guards mixed ARs | ✅ | — |
| 2.18 | Speaker diarization (`pyannote.audio` commented out in requirements) | 🟢 | L |
| 2.19 | yt-dlp subtitle reuse (`fetch_subs_on_long` downloads subs; Whisper always re-runs) | 🟢 | M |
| 2.20 | ~~UI design overhaul — "midnight terminal" system~~ ✅ midnight-green tokens + white hairline `--frame` border system, hard offset shadows, near-sharp radii; Space Grotesk (UI) + JetBrains Mono (labels/data); compact primitives (buttons h-8, inputs h-8, card p-4); help (?) icons removed — badges/labels/section headers now self-explain on hover; tooltips translucent (`bg-popover/70` + blur) | ✅ | — |

### 2d. Verified fine (audit false alarms — no action)

- `core/ingest.py` — intentional re-export shim, not a duplicate
- `core/export_bundle.py`, `core/splice.py` — implemented and tested
- `core/style_learning.py` — implemented + wired (GAP doc C9 "research" is stale)
- Per-clip webhooks — implemented (`pipeline_tasks.py:776+`; GAP C8 stale)

## 3. Test debt

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 3.1 | ~~Unit tests for `DistributionService`~~ ✅ `tests/test_distribution_service.py` — gates (approval, readiness, duration, connection, duplicate in-flight), ownership 404s, idempotency conflict/replay, schedule vs immediate enqueue | ✅ | — |
| 3.2 | ~~HTTP tests for `/api/distribution/*` and `/api/vault/*`~~ ✅ `tests/test_distribution_vault_http.py` — publish 202/error envelope, retry/cancel status guards, owner-scoped 404s, vault list/quota/save/delete. Also fixed vault delete returning 500 instead of 404, and a cached-Redis-across-event-loops bug in `conftest.py` that poisoned full-suite runs | ✅ | — |
| 3.3 | E2E publish flow (Playwright) — none exists; whole e2e suite gated on `E2E_RUN=1` | 🟡 | M |
| 3.6 | ~~Zero-test surfaces~~ ✅ assets API, splice validation, vault service/tasks, publish task paths, licensing helpers, webhook delivery (`tests/test_splice_module.py`, `test_vault_*.py`, `test_publish_tasks_coverage.py`, `test_licensing_misc.py`, `test_webhooks_delivery.py`). **Remaining:** tenant middleware (blocked on 2.10) | 🟡 | S |
| 3.4 | ~~`test_score_parallel_and_ensemble` fails locally (missing `ollama`)~~ ✅ `_build_client` now stubbed in the test — runs on hosts without worker deps | ✅ | — |
| 3.5 | ~~Coverage gate `fail-under=100`~~ ✅ gate ratcheting — was 75 (78.5% actual), now **`fail_under=82`** (82.7% actual, 418 tests). **110% plan:** line coverage maxes at 100%; next milestones 85 → 90 → 95 → 100 (+ branch coverage on hot paths) | 🟡 | L |
| 3.7 | **110% plan — next modules:** `core/tasks/pipeline_tasks.py` (86%), `backend/api/jobs.py`, `core/transcribe.py`, remaining `publish_tasks` TikTok path | 🟡 | M |

## 4. Windows desktop packaging (.exe)

**Current state:** an Electron shell exists at `apps/desktop`, but it is a **Docker
launcher** — `main.ts` requires Docker Desktop + `docker-compose.prod.yml`, which pulls
`ghcr.io/streamclip/*` images that don't exist yet. `scripts/install.ps1` also assumes
Docker Desktop. That is not a distributable .exe for end users.

**Decision required first (4.0):** Docker-in-desktop (bundle/require Docker, keep current
shell) vs **embedded runtime** (recommended: SQLite + in-process queue + bundled Python
sidecar, no Docker). Full rationale + implementation order:
`docs/ADR-001-desktop-packaging.md` (proposed, awaiting sign-off). Everything below
assumes embedded mode:

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 4.1 | **Database**: SQLite (aiosqlite) profile for SQLAlchemy + Alembic; audit migrations for Postgres-only DDL (JSONB, server defaults) | 🔴 | M |
| 4.2 | **Task queue**: Celery requires a broker (Redis). Options: (a) bundle a Redis-compatible sidecar (Memurai/redis-windows), (b) swap to in-process worker (threads/asyncio) behind the existing task interface, (c) SQLite-backed queue (huey). Decision needed — affects SSE progress relay too (Redis pub/sub) | 🔴 | L |
| 4.3 | **Storage**: `LocalStorage` backend already exists ✅ — verify presigned-URL code paths degrade cleanly (`file://` URLs in web UI) | 🟡 | S |
| 4.4 | **LLM**: Ollama optional — default desktop build to OpenAI/Anthropic API keys or bundled llama.cpp; degrade gracefully to score 0 (already does) | 🟡 | M |
| 4.5 | **ffmpeg**: bundle `ffmpeg.exe`/`ffprobe.exe`, resolve via app dir not PATH | 🔴 | S |
| 4.6 | **Python runtime**: PyInstaller/Nuitka build of FastAPI+worker. Torch (YOLO11/ultralytics) + CTranslate2 (faster-whisper) push bundle to multi-GB — consider ONNX export for YOLO and CPU-only torch wheel | 🔴 | L |
| 4.7 | **Web UI**: replace Next.js server with static export served by FastAPI, or wrap in Tauri/Electron with the Python backend as a sidecar process | 🔴 | L |
| 4.8 | **First-run experience**: model downloads (whisper, YOLO) with progress UI; workspace dir under `%LOCALAPPDATA%` | 🟡 | M |
| 4.9 | **Windows-isms audit**: path separators, long-path support, no POSIX shells in subprocess calls; verify `scripts/verify_stack.ps1` covers desktop mode | 🟡 | M |
| 4.10 | **Installer**: MSIX or Inno Setup; code signing certificate; auto-update strategy | 🟡 | M |
| 4.11 | **GPU detection**: NVENC/CUDA optional; CPU fallback must be default-safe (prod compose has no GPU worker profile) | 🟡 | S |
| 4.12 | **Licensing**: `/api/license/activate|status` exists — wire desktop activation UX (depends on 2.4/2.5) | 🟡 | M |
| 4.13 | **Electron shell fixes**: auto-updater is a stub (publish config points at placeholder GitHub repo); tray icon is `nativeImage.createEmpty()` (invisible); `package.json` references non-existent `apps/desktop/assets/`; preload exposes no IPC for stack control | 🟡 | M |
| 4.14 | **Prod compose gaps** (if Docker path chosen): no `STREAMCLIP_DISTRIBUTION__*` env vars, no `./assets` volume mount, single CPU worker on both queues | 🟡 | S |

## 5. macOS port (after Windows)

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 5.1 | ffmpeg with VideoToolbox hw accel (replace NVENC assumptions) | 🟡 | M |
| 5.2 | Torch on Apple Silicon (MPS) for YOLO; CTranslate2 arm64 wheels for whisper | 🟡 | M |
| 5.3 | App bundle (.app), codesigning + notarization, Gatekeeper | 🔴 | M |
| 5.4 | Paths: `~/Library/Application Support/StreamClip`; no `%LOCALAPPDATA%` | 🟢 | S |
| 5.5 | Universal2 vs separate arm64/x86_64 builds decision | 🟢 | S |
| 5.6 | Whatever queue decision made in 4.2 must be cross-platform (Memurai is Windows-only — favors in-process worker) | 🔴 | — |

## 6. Docs / env hygiene

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 6.1 | ~~TECHNICAL_DESIGN.md stale (social publish "out of scope")~~ ✅ updated to Rev 4 (2026-07-01) | — | — |
| 6.2 | ~~GAP_ANALYSIS.md stale rows~~ ✅ C3/C8/C9 marked shipped with evidence; T47 fixed at the source — `deploy/PRODUCTION.md` §1.3 now documents `STREAMCLIP_DISTRIBUTION__*` | ✅ | — |
| 6.3 | ~~Desktop packaging ADR~~ ✅ `docs/ADR-001-desktop-packaging.md` — recommends embedded runtime (SQLite + in-process worker + PyInstaller sidecar, no Docker) with implementation order for §4. **Awaiting sign-off (4.0)** | ✅ | — |
| 6.4 | ~~`.env.example` env-var mismatches~~ ✅ commerce vars renamed to `STREAMCLIP_COMMERCE__LEMON_SQUEEZY_*`; rate-limit opt-out now documented as dev-only (code default stays ON). `.env.production.example` keeps bare names — `docker-compose.prod.yml` maps them | ✅ | — |
| 6.5 | ~~README + CREATOR_PLATFORM.md stale~~ ✅ README roadmap checkboxes refreshed (webhooks/licensing shipped, Stripe row dropped), Windows venv activation noted; CREATOR_PLATFORM Now/Next/Later realigned with shipped features | ✅ | — |
| 6.6 | ~~`docs/cloud-deploy.md` aspirational~~ ✅ prominent design-stage banner added (nothing implemented; Stripe removed; keep-or-delete per 2.10) | ✅ | — |

## 7. Cleanup

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 7.1 | ~~Delete stray artifacts~~ ✅ verified clean 2026-07-02 — none of `.coverage`, `cov2.txt`, `coverage_term.txt`, `scripts/_fix_*.py` exist (removed in `7c32b2c`) | ✅ | — |
| 7.2 | ~~`backend/api/vault.py` excessive blank lines~~ ✅ reformatted | ✅ | — |
| 7.3 | ~~Narrow Celery `autoretry_for=(Exception,)` in `publish_tasks.py`~~ ✅ retries only transient errors (`httpx.TransportError`, `ConnectionError`, `TimeoutError`, `StorageError`); claim released back to `pending` before retry so re-claim works; domain failures fail fast | ✅ | — |
| 7.4 | ~~YouTube upload loads full file into memory~~ ✅ streams in 8 MB chunks (`_stream_file` async iterator in `youtube.py`) | ✅ | — |
| 7.5 | ~~Destinations drawer default tab~~ ✅ now defaults to `"publish"` | ✅ | — |
| 7.6 | ~~Deprecate `POST /api/jobs/{id}/clips/{clip_id}/publish`~~ ✅ marked `deprecated=True` in OpenAPI with pointer to `/api/distribution/publish`; route kept for external consumers; `openapi.ts` regenerated (also closes 2.15 — batch-publish intentionally stays on the jobs router) | ✅ | — |
