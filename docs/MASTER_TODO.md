# StreamClip — Master TODO (Release Readiness)

**Living document — running list of everything left before packaging and distributing
StreamClip as a Windows desktop executable, with a macOS port to follow.**

Last updated: 2026-07-02 · Owner: core team
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
| 2.1 | TikTok video upload stub (`core/distribution/tiktok.py:83–103`) — worker calls stub → publish jobs **always marked failed** when `TIKTOK_PUBLISH_ENABLED=true` (`publish_tasks.py:143–189`). Implement Content Posting API or keep flag off + honest UI | 🔴 | L |
| 2.2 | ~~Stripe billing stub~~ ✅ removed (`backend/api/billing.py` deleted, stub dropped from `core/billing.py`) — Lemon Squeezy is the sole provider | ✅ | — |
| 2.3 | ~~Lemon Squeezy webhook never persists keys~~ ✅ webhook now fail-closed on missing secret, verifies signature, persists issued keys idempotently (`install_licenses.status="issued"`, order id + email recorded); handles LS-native `license_key_created` events. **Remaining:** automated key delivery email for the `order_created` fallback path (key currently surfaced once in webhook response / LS log) | 🟡 | S |
| 2.4 | ~~License activation accepts any well-formed key~~ ✅ activation now requires a commerce-issued key (DB allowlist), rejects revoked keys, enforces `max_activations` across machine rebinds (migration `0007_license_issuance`) | ✅ | — |
| 2.5 | ~~Pick ONE billing provider~~ ✅ Lemon Squeezy chosen; chain wired: purchase → webhook → persisted key → activation → entitlement JWT → tier. Covered by `tests/test_license_chain.py` | ✅ | — |
| 2.6 | `COMMERCIAL.md` promises **Instagram Reels** OAuth publish as a Pro feature — no adapter exists. Ship it or cut the promise | 🟡 | L |

### 2b. Scaffolded-but-unwired

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 2.7 | Asset vault: full CRUD API (`backend/api/assets.py`) but **no web UI, no client methods**, and `core/overlay.py` reads filesystem manifest — never reads `Asset` DB rows (GAP U15) | 🟡 | L |
| 2.8 | Webhook settings: API exists (`/api/settings/webhook`) but settings page has no form and cites wrong path (`web/app/settings/page.tsx:56`); `settingsApi` client lacks webhook methods | 🟡 | S |
| 2.9 | Token refresh stub: `web/components/providers/token-refresh.tsx` POSTs empty `refresh_token` — non-functional session refresh | 🟡 | S |
| 2.10 | `backend/cloud/tenant.py` multi-tenant stub — not imported anywhere; `docker-compose.cloud.yml` sets `STREAMCLIP_CLOUD_MODE`/`STRIPE_*` that **no code reads**. Remove or finish | 🟡 | L |
| 2.11 | Onboarding wizard never calls `POST /api/devices/onboarding-complete` (cookie only) | 🟢 | S |
| 2.12 | Splice crossfade implemented in backend; UI always sends `transition: "cut"` (`web/app/actions/jobs.ts:194`) | 🟢 | S |
| 2.13 | `core/config.py:224` `lemon_squeezy_store_id` defined, never read | 🟢 | S |
| 2.14 | ~~License panel placeholder shows `STREAMCLIP-XXXX`~~ ✅ placeholder now `SCPRO-XXXX-XXXX-XXXX-XXXX` | ✅ | — |
| 2.15 | Duplicate job-scoped publish routes (`/api/jobs/.../publish`, `.../batch-publish`) vs distribution hub (GAP T49) — deprecate | 🟢 | M |

### 2c. Roadmap features (not started)

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 2.16 | Publish performance feedback loop — poll YouTube Analytics, feed style learning | 🟢 | L |
| 2.17 | Multi-aspect export (1:1, 16:9) — all presets 9:16 only | 🟢 | L |
| 2.18 | Speaker diarization (`pyannote.audio` commented out in requirements) | 🟢 | L |
| 2.19 | yt-dlp subtitle reuse (`fetch_subs_on_long` downloads subs; Whisper always re-runs) | 🟢 | M |

### 2d. Verified fine (audit false alarms — no action)

- `core/ingest.py` — intentional re-export shim, not a duplicate
- `core/export_bundle.py`, `core/splice.py` — implemented and tested
- `core/style_learning.py` — implemented + wired (GAP doc C9 "research" is stale)
- Per-clip webhooks — implemented (`pipeline_tasks.py:776+`; GAP C8 stale)

## 3. Test debt

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 3.1 | Unit tests for `DistributionService` (gates, idempotency, ownership) | 🔴 | M |
| 3.2 | HTTP tests for `/api/distribution/*` and `/api/vault/*` | 🔴 | M |
| 3.3 | E2E publish flow (Playwright) — none exists; whole e2e suite gated on `E2E_RUN=1` | 🟡 | M |
| 3.6 | Zero tests for: assets API, billing API, commerce webhook, splice API, TikTok adapter, tenant middleware | 🟡 | L |
| 3.4 | `tests/test_virality_twitch_misc.py::test_score_parallel_and_ensemble` fails locally (missing `ollama` package) — mock the import or add dev dependency | 🟢 | S |
| 3.5 | Coverage gate set to `fail-under=100` while actual is ~40% — set a realistic threshold | 🟡 | S |

## 4. Windows desktop packaging (.exe)

**Current state:** an Electron shell exists at `apps/desktop`, but it is a **Docker
launcher** — `main.ts` requires Docker Desktop + `docker-compose.prod.yml`, which pulls
`ghcr.io/streamclip/*` images that don't exist yet. `scripts/install.ps1` also assumes
Docker Desktop. That is not a distributable .exe for end users.

**Decision required first (4.0):** Docker-in-desktop (bundle/require Docker, keep current
shell) vs **embedded runtime** (recommended: SQLite + in-process queue + bundled Python
sidecar, no Docker). Everything below assumes embedded mode:

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
| 6.2 | GAP_ANALYSIS.md stale rows: C3 (editor exists), C8 (per-clip webhooks shipped), C9 (style learning shipped), T47 (PRODUCTION.md distribution vars) | 🟢 | S |
| 6.3 | Desktop packaging design doc (architecture decision record for 4.0) | 🟡 | M |
| 6.4 | `.env.example` `LEMON_SQUEEZY_*` names don't match `STREAMCLIP_COMMERCE__*` read by code; `RATE_LIMIT` default mismatch (true in code, false in example) | 🟡 | S |
| 6.5 | README roadmap checkboxes stale (webhooks are wired, default off); Unix-only venv instructions; `docs/CREATOR_PLATFORM.md` "Next/Later" lists shipped features | 🟢 | S |
| 6.6 | `docs/cloud-deploy.md` describes aspirational multi-tenant + Stripe metering — mark as design-stage or align with 2.10 decision | 🟢 | S |

## 7. Cleanup

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 7.1 | Delete stray artifacts: `.coverage`, `cov2.txt`, `coverage_term.txt`, `scripts/_fix_*.py` temp files | 🟢 | S |
| 7.2 | ~~`backend/api/vault.py` excessive blank lines~~ ✅ reformatted | ✅ | — |
| 7.3 | Narrow Celery `autoretry_for=(Exception,)` in `publish_tasks.py` | 🟡 | S |
| 7.4 | YouTube upload loads full file into memory — stream instead | 🟡 | S |
| 7.5 | ~~Destinations drawer default tab~~ ✅ now defaults to `"publish"` | ✅ | — |
| 7.6 | Deprecate `POST /api/jobs/{id}/clips/{clip_id}/publish` (web uses `/api/distribution/publish`) | 🟢 | S |
