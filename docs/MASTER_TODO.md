# StreamClip — Master TODO (Release Readiness)

**Living document — running list of everything left before packaging and distributing
StreamClip as a Windows desktop executable, with a macOS port to follow.**

Last updated: 2026-07-07 (plan audit + desktop §4.1–4.5) · Owner: core team  
Legend: 🔴 blocker · 🟡 important · 🟢 nice-to-have | Effort: S (<1d) M (1–3d) L (1w+)

**Desktop embedded runtime (ADR-001):** §4.1–4.5 ✅ · §4.6 scaffold ✅ · §4.7 + §4.7a static export ✅ · §4.13 Electron sidecar shell ✅ · Next: full PyInstaller ML bundle.

**Cross-refs:** [`docs/BETA_TESTER_PLAN.md`](BETA_TESTER_PLAN.md) · [`docs/BETA_GO_LIVE.md`](BETA_GO_LIVE.md) · [`docs/GAP_ANALYSIS.md`](GAP_ANALYSIS.md) · [`docs/ADR-001-desktop-packaging.md`](ADR-001-desktop-packaging.md)

---

## 1. Ship the current changeset (do first)

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 1.1 | ~~Commit the uncommitted diff~~ ✅ committed `7c32b2c` (temp scripts + coverage artifacts deleted, `.gitignore` tightened) | ✅ | — |
| 1.2 | ~~Run `alembic upgrade head`~~ ✅ through `0007_license_issuance` on dev stack. **Current head:** `0009_phase3_trust_ops` — rerun `alembic upgrade head` on every deploy | 🟡 | S |
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
| 2.3 | ~~Lemon Squeezy webhook never persists keys~~ ✅ webhook now fail-closed on missing secret, verifies signature, persists issued keys idempotently (`install_licenses.status="issued"`, order id + email recorded); handles LS-native `license_key_created` events. **Remaining:** automated key delivery email for the `order_created` fallback path (key currently surfaced once in webhook response / LS log) | 🟡 | S |
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
| 2.10 | `backend/cloud/tenant.py` multi-tenant stub — header → context var only; not wired into routes. Covered by `tests/test_cloud_tenant.py`. `docker-compose.cloud.yml` sets env vars **no code reads**. Remove or finish | 🟡 | L |
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

- `core/ingest.py` — intentional re-export shim, not a duplicate
- `core/export_bundle.py`, `core/splice.py` — implemented and tested
- `core/style_learning.py` — implemented + wired (GAP doc C9 "research" is stale)
- Per-clip webhooks — implemented (`pipeline_tasks.py:776+`; GAP C8 stale)

## 3. Test debt

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 3.1 | ~~Unit tests for `DistributionService`~~ ✅ `tests/test_distribution_service.py` | ✅ | — |
| 3.2 | ~~HTTP tests for `/api/distribution/*` and `/api/vault/*`~~ ✅ `tests/test_distribution_vault_http.py` | ✅ | — |
| 3.3 | E2E publish flow (Playwright) — smoke behind `E2E_RUN=1`; extend to upload → clips → approve → publish queue (`BETA_TESTER_PLAN` §1, `BETA_GO_LIVE` §2) | 🟡 | M |
| 3.4 | ~~`test_score_parallel_and_ensemble` fails locally (missing `ollama`)~~ ✅ `_build_client` stubbed in test | ✅ | — |
| 3.5 | Coverage gate ratchet — **`fail_under=95`** green (~95%). **110% plan:** 100% line + hot-path branches + Playwright smoke (`BETA_GO_LIVE` §1) | 🟡 | L |
| 3.6 | ~~Zero-test surfaces~~ ✅ batches 1–3. **Remaining:** Playwright e2e (§3.3) | 🟡 | S |
| 3.7 | **110% plan — next modules:** `core/tasks/pipeline_tasks.py` remaining ~76 lines, branch coverage on `backend/services/sse.py` + distribution OAuth + `job_service` | 🟡 | M |
| 3.8 | **`verify_stack.ps1` on clean Windows 11 VM** — required before Phase 0 invites (`BETA_GO_LIVE` §2, `BETA_TESTER_PLAN` §1) | 🟡 | S |
| 3.9 | Desktop verify scripts in CI or release checklist: `verify_desktop_db.ps1`, `verify_inprocess.ps1`, `verify_desktop_storage.ps1`, `verify_desktop_ffmpeg.ps1` | 🟡 | S |

## 4. Windows desktop packaging (.exe)

**Current state:** Electron shell at `apps/desktop` is still a **Docker launcher** (`docker-compose.prod.yml`, `ghcr.io/streamclip/*`). Embedded runtime seam is partially built (§4.1–4.5 ✅).

**Decision (4.0):** ✅ **Accepted 2026-07-07** — embedded runtime (SQLite + in-process queue + bundled Python sidecar, no Docker). Rationale: `docs/ADR-001-desktop-packaging.md`.

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 4.1 | **Database**: ✅ SQLite (aiosqlite) profile + portable Alembic migrations (`backend/db/types.py`, `config/desktop.yaml`) | 🟢 | M |
| 4.2 | **Task queue**: ✅ In-process worker (`core/inprocess_worker.py`, `core/task_runner.py`, memory progress bus). Enable via `STREAMCLIP_QUEUE__BACKEND=inprocess` or `config/desktop.yaml` | 🟢 | L |
| 4.3 | **Storage**: ✅ LocalStorage served via `/storage/{key}` (GET/PUT); Next.js rewrite proxies same-origin; `test_local_storage_http.py` | 🟢 | S |
| 4.4 | ~~LLM desktop defaults~~ ✅ `config/desktop.yaml` documents `STREAMCLIP_LLM__PROVIDER=openai|anthropic` + key env; shorter 30s timeout; no-LLM path degrades to score 0 (`core/virality.py:301`) with ensemble still ranking | ✅ | — |
| 4.5 | **ffmpeg**: ✅ `core/ffmpeg_bins.py` resolves bundled `bin/ffmpeg/` or PATH; all pipeline call sites use `ffmpeg_bin()` / `ffprobe_bin()` | 🟢 | S |
| 4.6 | **Python runtime**: ✅ **Scaffold** — `desktop_sidecar/run.py`, PyInstaller spec, `build_sidecar.ps1`. **Remaining:** full ML bundle size (torch/whisper), CPU-only wheels, ONNX YOLO | 🟡 | L |
| 4.7 | **Web UI**: ✅ Static export — `backend/static_ui.py`, `NEXT_STATIC_EXPORT=1` build, `build_desktop_ui.ps1`, client actions in `web/lib/api/actions/` | 🟢 | L |
| 4.8 | **First-run experience**: model downloads (whisper, YOLO) with progress UI. Data dir ✅ done via §4.18 (`%LOCALAPPDATA%\StreamClip`) | 🟡 | M |
| 4.9 | **Windows-isms audit**: path separators, long-path support, no POSIX shells in subprocess calls; extend verify scripts for desktop mode | 🟡 | M |
| 4.10 | **Installer**: MSIX or Inno Setup; code signing certificate; auto-update strategy | 🟡 | M |
| 4.11 | **GPU detection**: NVENC/CUDA optional; CPU fallback must be default-safe (prod compose has no GPU worker profile) | 🟡 | S |
| 4.12 | **Licensing**: `/api/license/activate|status` exists — wire desktop activation UX (depends on 2.4/2.5) | 🟡 | M |
| 4.13 | **Electron shell**: ✅ Spawns sidecar (`python -m desktop_sidecar` dev / bundled exe prod), BrowserWindow at `http://127.0.0.1:8765/`, preload IPC (start/stop/health), tray icon fallback, auto-updater stub | 🟢 | M |
| 4.14 | **Prod compose gaps** (Docker self-host path): no `STREAMCLIP_DISTRIBUTION__*` env vars, no `./assets` volume mount, single CPU worker on both queues (GAP T56) | 🟡 | S |
| 4.15 | **Alembic `upgrade head` on desktop sidecar startup** — ✅ in `desktop_sidecar/run.py` | 🟢 | S |
| 4.16 | **`scripts/verify_desktop.ps1`** — aggregate db + storage + ffmpeg smoke (inprocess optional via `verify_inprocess.ps1`) | 🟢 | S |
| 4.17 | **Full in-process parity**: ✅ all direct Celery `.delay()` / `send_task` (distribution, commerce, support, vault, CLI) routed through `core/task_dispatch.py` / `task_runner`; in-process Beat loop fires scheduled publishes + cleanup (`queue.inprocess_beat`, only while app runs — see BETA_KNOWN_ISSUES) | 🟢 | M |
| 4.7a | **Server Actions migration** — ✅ `web/lib/api/actions/*` + `client-session.ts`; components use client API; BFF routes moved to `web/app/_api_bff/` | 🟢 | L |
| 4.18 | **Production desktop config profile** — ✅ frozen builds (or `STREAMCLIP_DESKTOP_DATA_DIR`) resolve DB/storage/workspace/cache under `%LOCALAPPDATA%\StreamClip` (`~/.streamclip` fallback) via env overrides in `desktop_sidecar/run.py`; config file keeps dev defaults | 🟢 | S |

## 5. macOS port (after Windows)

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 5.1 | ffmpeg with VideoToolbox hw accel (replace NVENC assumptions) | 🟡 | M |
| 5.2 | Torch on Apple Silicon (MPS) for YOLO; CTranslate2 arm64 wheels for whisper | 🟡 | M |
| 5.3 | App bundle (.app), codesigning + notarization, Gatekeeper | 🔴 | M |
| 5.4 | Paths: `~/Library/Application Support/StreamClip`; no `%LOCALAPPDATA%` | 🟢 | S |
| 5.5 | Universal2 vs separate arm64/x86_64 builds decision | 🟢 | S |
| 5.6 | In-process worker from 4.2 is cross-platform ✅ (no Memurai/Redis broker required on desktop) | 🟢 | — |

## 6. Docs / env hygiene

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 6.1 | ~~TECHNICAL_DESIGN.md stale (social publish "out of scope")~~ ✅ updated to Rev 4 (2026-07-01) | ✅ | — |
| 6.2 | ~~GAP_ANALYSIS.md stale rows~~ ✅ C3/C8/C9 marked shipped with evidence; T47 fixed at the source | ✅ | — |
| 6.3 | ~~Desktop packaging ADR~~ ✅ `docs/ADR-001-desktop-packaging.md` — **Accepted 2026-07-07** | ✅ | — |
| 6.4 | ~~`.env.example` env-var mismatches~~ ✅ commerce vars renamed; rate-limit opt-out documented as dev-only | ✅ | — |
| 6.5 | ~~README + CREATOR_PLATFORM.md stale~~ ✅ partial refresh 2026-07-01. **Remaining:** README project layout (GAP T54), CREATOR_PLATFORM vault/desktop rows | 🟡 | S |
| 6.6 | ~~`docs/cloud-deploy.md` aspirational~~ ✅ design-stage banner added (keep-or-delete per 2.10) | ✅ | — |
| 6.7 | ~~README project layout~~ ✅ layout refreshed: `core/ingest/`, router list, migrations `0001`–`0009`, desktop paths (`desktop_sidecar/`, `packaging/`, `static/ui/`, `bin/ffmpeg/`, `config/desktop.yaml`) | ✅ | — |
| 6.8 | ~~GPU queue narrative~~ ✅ `worker` queues now `${STREAMCLIP_WORKER_QUEUES:-default,gpu}` — set `default` with `--profile gpu` for true isolation; README ship checklist updated (GAP T56) | ✅ | — |
| 6.9 | ~~Reframe `auto` preset~~ ✅ README table already says "clip emotion heuristics"; TDD has no LLM-picks wording (GAP T57 stale) | ✅ | — |
| 6.10 | ~~`CREATOR_PLATFORM.md` sync~~ ✅ asset vault end-to-end + desktop §4.1–4.5 marked shipped; Next section updated to §4.6–4.13 | ✅ | — |
| 6.11 | ~~`.cursor/skills/streamclip-development/SKILL.md`~~ ✅ desktop profile section added (SQLite, inprocess queue, sidecar, static UI, verify scripts) | ✅ | — |
| 6.12 | ~~`docs/BETA_TESTER_PLAN.md` §2~~ ✅ hard blocker 4.0 marked accepted 2026-07-07 | ✅ | — |

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
technical) → Phase 1 (creator closed, GHCR/hosted) → Phase 2 (desktop `.exe`). Do **not**
invite external testers until §1 gate in that doc is green (100% line + hot-path branches +
Playwright smoke + `verify_stack.ps1`).

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 8.1 | Hit 110% coverage gate (§3.5 → 100% line + §3.7 branches + §3.3 Playwright) | 🔴 | L |
| 8.2 | ~~Write `docs/BETA_TESTER_QUICKSTART.md` at Phase 0 open~~ ✅ exists | ✅ | S |
| 8.3 | Phase 0 cohort (5–10): Docker self-host, T0 flows in beta plan | 🟡 | M |
| 8.4 | Phase 1: LS license email (2.3) + 20–40 creators + optional GHCR tags | 🟡 | M |
| 8.5 | Phase 2: desktop closed beta (§4.6–4.8 minimum) — 50–100 testers | 🔴 | L |
| 8.6 | Align commerce docs/code to one-time purchase (perpetual entitlement) before paid Phase 1 (`COMMERCIAL.md`, `core/licensing.py`, LS product config) | 🟡 | S |
| 8.7 | **`docs/BETA_KNOWN_ISSUES.md`** — TikTok inbox-only, no Instagram, CPU fallback SLAs, SmartScreen unsigned desktop (beta kit item in `BETA_TESTER_PLAN` §4.2) | 🟢 | S |
| 8.8 | **GHCR image build + publish workflow** — `ghcr.io/streamclip/*` referenced by `apps/desktop` / prod compose but images do not exist (`BETA_TESTER_PLAN` §5.1 Option A) | 🟡 | M |
| 8.9 | **Beta launch ops** (`BETA_GO_LIVE` §2–§4): feedback channel (Discord/Discussions), clean VM verify, OAuth redirect URIs match `WEB_ORIGIN`, on-call rotation, changelog per wave | 🟡 | M |
| 8.10 | Flip `docs/BETA_TESTER_PLAN.md` status **Draft → Active** when §8.1 gate is green | 🟡 | S |

## 9. Self-host / ops (Docker path — parallel to desktop)

| # | Item | Sev | Effort |
|---|------|-----|--------|
| 9.1 | **`/api/health/stack` deep probe** documented in beta flows (T0-1) — verify endpoint covers worker, beat, minio, redis, postgres | 🟢 | S |
| 9.2 | **Prometheus/Grafana or log tail procedure** for opt-in beta testers (`BETA_GO_LIVE` §3, `BETA_TESTER_PLAN` §7) | 🟢 | S |
| 9.3 | **MkDocs internal docs site** — maintain `mkdocs.yml`, Vercel deploy, keep `GAP_ANALYSIS` / `MASTER_TODO` in `exclude_docs` (`docs/INTERNAL.md`) | 🟢 | S |

---

## Plan sync checklist (agents)

When closing work from any plan doc, update **this file** and the source plan:

| Source | Update MASTER_TODO when… |
|--------|-------------------------|
| `GAP_ANALYSIS.md` | New T/U/C gap or deferral changes |
| `BETA_TESTER_PLAN.md` | Phase gates, kit contents, exit criteria |
| `BETA_GO_LIVE.md` | Launch checklist items move |
| `ADR-001-desktop-packaging.md` | Desktop implementation order advances |
| `CREATOR_PLATFORM.md` | Roadmap Now/Next/Later shifts |

Invoke skill: **streamclip-gap-analysis** for full doc/code drift audits.
