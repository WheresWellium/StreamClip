# qClip — Technical Design

**Revision:** 5 (2026-07-31)  
**Status:** Active
**Primary product:** the **Windows/macOS desktop installer** (Electron shell + embedded Python sidecar). The Docker stack is a **dev + future Pro self-host** runtime, not the shipped product — see [ADR-001](ADR-001-desktop-packaging.md) and [Appendix D](#appendix-d--docker-self-host-runtime-dev--future-pro).

> **Rev 5 re-center (why this doc changed):** Revs 1–4 described the Docker stack as *the* architecture. The product is the `.exe` a creator double-clicks. That drift is the documented root cause of "works locally, breaks for other Windows users" ([DESKTOP_FAILURE_TAXONOMY.md](DESKTOP_FAILURE_TAXONOMY.md) F11). This revision makes the **desktop path canonical**; the shared `core/` pipeline is unchanged and reused by both runtimes.

## 1. Purpose & scope

qClip is an **all-in-one desktop clip studio**: a creator installs one app, pastes a URL or drops a file, and gets social-ready clips (9:16 default; 1:1, 4:5, 16:9, 2:3 selectable) with auto-reframe, karaoke captions, optional meme overlays, comparative virality ranking, and one-click publish — **no Docker, no CLI, no cloud account required**. Everything runs on the user's own machine (GPU when present, CPU otherwise).

**In scope (product):** installer + embedded runtime, ingest, transcription, highlight discovery, post-hoc virality, per-clip render, local web UI served by the sidecar, license activation, social distribution (YouTube publish, TikTok inbox, scheduling while app is open, Clip Vault), style learning, first-run model download, GPU auto-detection.
**Shared with Docker (reused, not product):** the entire `core/` pipeline, `backend/` API, DB models, Alembic migrations.
**Out of scope (roadmap):** speaker diarization, TikTok direct-post (`video.publish` audit pending), Instagram Reels, EV code-signing (in progress), managed cloud SKU.
Billing is Lemon Squeezy (perpetual license keys); Stripe was dropped.

### 1.1 Two runtimes, one core (the seam)

The product and the dev/Pro stack share `core/` and diverge only by **three config switches**. This is the single most important thing to master:

| Switch | Desktop (product) | Docker (dev / Pro) | Code |
|--------|-------------------|--------------------|------|
| `queue.backend` | `inprocess` (thread pools) | `celery` (Redis broker) | `core/task_dispatch.py`, `core/task_runner.py`, `core/inprocess_worker.py` |
| `database.url` | `sqlite+aiosqlite` | `postgresql+asyncpg` | `backend/db/types.py` portable DDL |
| `storage.backend` | `local` (LocalStorage + `/storage/{key}`) | `minio` (S3 presigned) | `core/storage.py`, `backend/static_ui.py` |

Progress transport follows the queue switch: desktop uses the **in-memory progress bus** (`core/progress_bus.py`, a Redis-shaped snapshot + pub/sub) feeding the same SSE endpoints; Docker uses Redis pub/sub. **Any code that assumes Celery/Redis directly is a drift bug** (taxonomy F10).

## 2. Goals & non-goals

| Goal | Non-goal |
|------|----------|
| **Zero-friction install** — double-click `.exe`, no Docker/CLI/cloud | Requiring devops from creators |
| **Wall-clock throughput** on a single machine (GPU or CPU) | Feature breadth without perf budget |
| **Legible failure** — never a silent white screen or eternal spinner | Cryptic 500s / blank windows |
| Runs offline; user's own GPU | Mandatory cloud APIs |
| Guaranteed clip output (always N clips) | Virality gating clip creation |
| Post-hoc virality for ranking & splice UX | Perfect LLM accuracy on first pass |
| Word-level caption sync on rendered clips | Generic subtitle burn without re-transcribe |
| Idempotent clip render (skip if done) | Re-running full pipeline on retry |
| One shared `core/` for desktop + Pro | Two forked pipelines |

## 3. Runtime architecture (desktop — the product)

```
User double-clicks qClip-Setup-win-x64.exe
        │
        ▼
Electron tray shell (apps/desktop/src/main.ts)
   │  spawns + supervises, picks a free port, shows splash then UI
   ▼
Python sidecar  (streamclip-sidecar.exe, PyInstaller one-dir)  ── http://127.0.0.1:8765
   ├─ FastAPI (backend/main.py)  ── serves API + static Next.js UI (backend/static_ui.py)
   ├─ InProcessWorker (core/inprocess_worker.py)  ── default pool + single-slot GPU pool + Beat thread
   ├─ MemoryProgressBus (core/progress_bus.py)  ── SSE progress, no Redis
   ├─ SQLite (aiosqlite)  ── %LOCALAPPDATA%\StreamClip\streamclip.db
   ├─ LocalStorage  ── %LOCALAPPDATA%\StreamClip\storage, served at /storage/{key}
   └─ bundled ffmpeg/ffprobe (bin/ffmpeg) + first-run model download (core/model_prefetch.py)
        │
        ▼
Shared core/ pipeline  (ingest → transcribe → highlights → virality → process_clip × N → finalise)
```

**Everything is one process tree on one machine.** No broker, no object store, no second server. The Electron shell's only job is to spawn/supervise the sidecar and show its UI (or a legible error page when it can't).

### 3.1 Desktop components

| Component | Path | Role |
|-----------|------|------|
| Electron shell | [apps/desktop/src/main.ts](../apps/desktop/src/main.ts) | Spawn/supervise sidecar, free-port resolution, single-instance lock, splash + `startup-error.html`, tray (Open / Restart engine / Open engine log), auto-updater |
| Sidecar bootstrap | [desktop_sidecar/run.py](../desktop_sidecar/run.py) | Resolve data dir (`%LOCALAPPDATA%\StreamClip`), apply GPU env, **fail-fast on unwritable dirs**, Alembic upgrade, seed licenses, model prefetch, `uvicorn.run` |
| In-process worker | [core/inprocess_worker.py](../core/inprocess_worker.py) | `default_pool` (`queue.default_workers`) + `gpu_pool` (concurrency=1, mirrors the `gpu` queue) + Beat thread; invokes `on_failure` directly (no broker) so failed jobs never hang |
| Progress bus | [core/progress_bus.py](../core/progress_bus.py) | In-memory snapshot + async pub/sub with monotonic `event_id`; SSE + `Last-Event-Id` replay without Redis |
| Static UI mount | [backend/static_ui.py](../backend/static_ui.py) | Serves exported Next.js from `static/ui`; SPA shells for `/jobs/[id]`; reserves `/api`, `/storage`, `/metrics` |
| GPU profile | [core/gpu_profile.py](../core/gpu_profile.py) | Detect CUDA/NVENC/MPS; upgrade when present, **downgrade to CPU/libx264 when absent** |
| Packaging | [packaging/pyinstaller/streamclip-sidecar.spec](../packaging/pyinstaller/streamclip-sidecar.spec) | One-dir ML bundle (~1.1 GB); **aborts build** if a critical pkg (torch/ctranslate2/faster_whisper) fails to collect; weights download at runtime |

### 3.2 Boot sequence (fresh install)

1. Electron `whenReady` → `resolveSidecarPort()` (default 8765, relocates only if busy and not pinned).
2. Spawn sidecar; window opens on **splash** immediately (no white flash — `backgroundColor #0a0f1c`).
3. Sidecar: `configure_desktop_env` → data dir under `%LOCALAPPDATA%` → `verify_writable()` → **`SystemExit(1)` if any path is unwritable** (F1) → Alembic `upgrade head` on SQLite → seed cohort licenses → background model prefetch → `uvicorn`.
4. Electron polls `/api/health` (fast 200 ms for 10 s, then 750 ms, 180 s budget). On healthy → `loadURL(sidecar)`. On death/timeout → `startup-error.html` with reason + log path + Retry/Restart.
5. Tray notification "qClip is running".

### 3.3 Request paths (desktop)

1. **URL job:** UI → `POST /api/jobs` with `source_url` → in-process worker ingests via yt-dlp → `%LOCALAPPDATA%\StreamClip\workspace\jobs\{id}\source.mp4`.
2. **Upload job:** `POST /api/uploads/init` → browser PUT to **same-origin** `/storage/{key}` (LocalStorage; no MinIO) → `POST /api/jobs` with `source_upload_key`.
3. **Auth:** single-user desktop typically runs `allow_anonymous`; license activation gates Pro features, not login.

*(The Docker request paths — presigned MinIO, Celery enqueue, JWT — live in [Appendix D](#appendix-d--docker-self-host-runtime-dev--future-pro).)*

## 4. Pipeline design

**FigJam:** [Pipeline flow](https://www.figma.com/board/hnq3vqD7QXKPfTk3eBw0fo)

### 4.1 Task chain

```
start_pipeline
  → run_ingest
  → run_transcribe
  → run_highlights
  → run_virality_scores
  → fan_out_clips
      → chord(process_clip × N, finalise_job)
  → (beat) cleanup_expired_jobs hourly
  → (beat) process_due_scheduled_jobs — scheduled publish poller

Distribution (out-of-band, default queue):
  publish_clip_to_platform   — upload from MinIO → YouTube; SSE progress via Redis
  copy_clip_to_vault         — vault_tasks.py; quota + approval gated
```

| Task | Queue | Input | Output | Failure behavior |
|------|-------|-------|--------|------------------|
| `run_ingest` | default | URL or upload key | `source.mp4`, `config_snapshot` tier hints | Job → `error` |
| `run_transcribe` | gpu | `source.mp4` | `transcript.json` (word timestamps) | Retry; job → `error` |
| `run_highlights` | default | transcript + signals | Clip rows (discovery scores) | `_guaranteed_clips()` fallback |
| `run_virality_scores` | default | clip windows + transcript | `llm_score`, emotion, reranked `ensemble_score` | Degrades to score 0 |
| `process_clip` × N | gpu | clip boundaries | vertical MP4, thumb, optional `clip_XX_transcript.json` | Per-clip error; others continue |
| `finalise_job` | default | chord results | job `done`/`error`, quota minutes, webhook | Always runs |
| `cleanup_expired_jobs` | beat | retention config | purged jobs + storage | Logs per-key failures |

**Source:** `core/tasks/pipeline_tasks.py`, `core/celery_app.py`

### 4.2 Ingest (`core/ingest/`)

- `IngestService` normalizes URL / upload / local → `workspace/jobs/{id}/source.mp4`
- **Tiers:** `short` (<2 min), `medium`, `long` — control download height and `pipeline_hints`
- **Long VODs:** optional `--write-auto-subs` via `ingest.fetch_subs_on_long` (subs cached; Whisper still runs on audio)
- URL-hash disk cache in `cache_dir` avoids re-download
- Uploads keep original storage key (no re-upload)

### 4.3 Highlight detection (`core/highlights.py`)

Discovery signals — **no LLM at discovery**:

| Signal | Module | Notes |
|--------|--------|-------|
| Audio energy | `highlights.py` | librosa RMS, 90th-percentile windows |
| Spectral novelty | `highlights.py` | Onset strength |
| Optical flow | `highlights.py` | Farneback; skippable on short tier |
| Twitch chat spikes | `core/chat_spikes.py` | Message-rate vs baseline |
| Peak discovery | `core/peak_detection.py` | Audio + chat local maxima, smooth, merge |

**Candidate modes** (`highlight.candidate_mode`): `segments` | `peaks` | `hybrid` (default).

**Content profiles** (`core/content_profiles.py`): per-job `content_profile` tunes weights across 9 verticals — gaming, esports, irl, vlog, podcast, education, sports, music, general. Catalog with UI labels lives in `core/creator_options.py` (single source of truth for `/api/meta`).

- NMS + boundary snap to word edges when transcript available
- `_guaranteed_clips()` ensures clip rows always exist

### 4.3b Virality scoring (`core/virality.py`)

Post-hoc LLM metric on finished clip transcripts — **never gates clip creation**.

1. `run_virality_scores` runs after highlights, before render fan-out
2. `build_virality_prompt()` assembles a **profile-aware prompt**: one persona + viral/anti-viral criteria per content profile (9 variants), plus optional `ClipScoringContext` evidence — measured signal telemetry (audio/spectral/flow/chat), sampled live-chat excerpts (`select_chat_excerpts`), and ±30s surrounding transcript
3. `score_clip_virality()` → JSON: score 0–100, emotion, meme_keywords
4. `ensemble_with_virality()` recomputes rank using profile or `highlight.weight_*`; `meme_keywords` persisted on `Clip` for overlay matching
5. Clips reranked by `ensemble_score` before `fan_out_clips`

**LLM providers:** `ollama` (default), `openai`, `anthropic` — `core/virality.py::_build_client`

### 4.3c Style learning (`core/style_learning.py`)

Per-user, per-profile signal-weight nudges (±0.02, 70/30 default blend):

- **Explicit:** `POST /api/settings/clips/{id}/feedback` star ratings
- **Implicit:** clip approve (→5) / reject (→1) via `backend/services/feedback_service.py`

### 4.4 Transcription & captions

| Stage | Module | Behavior |
|-------|--------|----------|
| Full source | `core/transcribe.py` | faster-whisper, VAD on, word timestamps |
| Per-clip refine | `transcribe_clip()` | Re-transcribes extracted segment; VAD off; 0-based times |
| Timing repair | `core/caption_timing.py` | Overlap collection, snap to words, karaoke `\k` tags |
| ASS burn | `core/captions.py` | Style presets; word-level sync when `caption.word_level_sync` |

**Accuracy path:** output-side ffmpeg seek (`core/ffmpeg_utils.extract_segment`) + clip re-transcribe + word snap.

### 4.5 Clip processing (`process_clip`)

```
extract → reframe → caption → overlay → validate duration → thumbnail → upload
```

| Step | Module | Notes |
|------|--------|-------|
| Extract | `core/ffmpeg_utils.py` | `-i` then `-ss` (output seek), `avoid_negative_ts make_zero` |
| Reframe | `core/reframe.py` | YOLO11 + ByteTrack, Gaussian-smoothed path |
| Caption | `core/captions.py` | Full-job transcript + optional clip transcript |
| Overlay | `core/overlay.py` | Semantic keyword → GIF/SFX from `assets/manifest.json` |
| Validate | `ffmpeg_utils.validate_output_duration` | ±1.5s tolerance vs source window |
| Idempotency | `process_clip` | Skip if `status=done` and `final_storage_key` set |

Encode via `core/export_video.py` ← `ExportConfig` (`codec`, `crf`, `fps` ≥ 60).

### 4.6 Reframe (`core/reframe.py`)

YOLO11 + ByteTrack tracking, Gaussian-smoothed camera path, preset HUD zones.  
`MIN_SMOOTH_WINDOW_FRAMES = 60` floor regardless of preset.

## 5. Data model

### 5.1 Postgres (`backend/db/models.py`)

| Entity | Key fields |
|--------|------------|
| `User` | email, hashed password, `jobs_used_this_month`, `minutes_processed_this_month`, `style_weights` |
| `Job` | `owner_id`, status, stage, progress, `config_snapshot`, storage keys |
| `Clip` | start/end, scores (`audio`, `spectral`, `flow`, `llm`, `ensemble`), emotion, `approval_status`, storage keys |
| `ClipFeedback` | per-user clip ratings feeding style learning |
| `VaultClip` | saved clips (quota + approval gated), migration `0006` |
| `InstallOAuthApp` | BYO OAuth app credentials per platform (encrypted) |
| `PublishJob` | platform, status, schedule time, idempotency key, result URL |
| `Asset` | asset vault API (`backend/api/assets.py`); no management UI yet |

### 5.2 MinIO key layout

```
uploads/{uuid}/...
jobs/{job_id}/source/source.mp4
jobs/{job_id}/transcript/transcript.json
jobs/{job_id}/clips/clip_{NN}_final.mp4
jobs/{job_id}/clips/clip_{NN}_thumb.jpg
jobs/{job_id}/clips/clip_{NN}_transcript.json   # when refine_clip_transcript
```

### 5.3 Redis

| Key pattern | Purpose |
|-------------|---------|
| Celery broker DB 1 | Task queue |
| Celery results DB 2 | Task results |
| `streamclip:progress:{job_id}` | Latest progress JSON |
| `streamclip:progress:{job_id}:seq` | Monotonic SSE `event_id` |

## 6. Configuration

Two profiles, one schema (`core/config.py` `Settings`):

- **Desktop (product):** [config/desktop.yaml](../config/desktop.yaml) — `queue.backend: inprocess`, `storage.backend: local`, SQLite URLs, `whisper.model_size: medium` + `device: cpu` + `compute_type: int8`, `weight_optical_flow: 0`, `refine_clip_transcript: false`, `rate_limit.enabled: false`, `web.serve_static: true`. Frozen builds relocate DB/storage/workspace/cache/output/license under `%LOCALAPPDATA%\StreamClip` via env overrides ([desktop_sidecar/run.py](../desktop_sidecar/run.py) `configure_data_dirs`).
- **Docker (dev/Pro):** `config.yaml` — Postgres, MinIO, Celery, Ollama, large-v3 defaults.

**Critical invariant (F12):** desktop env overrides must be applied **before** `backend.main` import (modules cache `get_settings()` at import time), so `run_server` sets env, then imports the app ([desktop_sidecar/run.py](../desktop_sidecar/run.py) ~158–161). A packaged exe that skips this silently falls back to `large-v3` + optical flow.

**Writable-path registry (F1):** every path that gets written is registered in `Settings._writable_slots()` — `workspace_dir`, `output_dir`, `cache_dir`, `storage.local_root`, `licensing.license_file`. `ensure_dirs()` relocates unwritable ones off read-only prefixes; `verify_writable()` fail-fasts at sidecar start. Enforced by `tests/test_config.py::test_writable_slots_registry_is_complete`. **Never add an ad-hoc write path — add a slot.**

`config.yaml` + `STREAMCLIP_*` env vars → `core/config.py` (`Settings`).

| Sub-config | Key fields |
|------------|------------|
| `whisper` | `model_size`, `clip_vad_filter`, `min_word_probability` |
| `llm` | `provider`, `model`, `base_url`, `api_key` |
| `highlight` | weights (sum 1.0), `target_clips`, durations |
| `caption` | `word_level_sync`, `refine_clip_transcript`, `word_hold_secs` |
| `export` | `codec`, `fps` (≥60), `crf` |
| `ingest` | tier heights, `fetch_subs_on_long`, optical-flow skips |
| `auth` | `secret_key`, `allow_anonymous` |
| `job_retention` | `retention_days`, `batch_size` |
| `webhooks` | `enabled`, `url`, `secret`, retries |
| `observability` | `sentry_dsn`, `otel_endpoint`, `enable_metrics` |
| `rate_limit` | `jobs_per_hour`, `requests_per_minute` |

## 7. API & web contract

### 7.1 REST endpoints

| Route | Purpose |
|-------|---------|
| `POST /api/jobs` (+`/batch`) | Create job(s) (URL or upload key) |
| `GET /api/jobs`, `GET /api/jobs/{id}` | List/detail; owner-scoped when auth enabled |
| `DELETE /api/jobs/{id}` | Cancel + delete job |
| `PATCH /api/jobs/{id}/clips/{clip_id}/approval` | Approve/reject clip (feeds implicit style learning) |
| `POST /api/jobs/{id}/clips/{clip_id}/publish` | Legacy publish — superseded by `/api/distribution/publish` |
| `POST /api/uploads/init` | Presigned PUT URL |
| `POST /api/auth/register\|login\|refresh` | JWT issuance |
| `GET /api/auth/me` | Current user |
| `GET /api/distribution/platforms\|connections\|publish-jobs` | Distribution hub reads |
| `POST /api/distribution/publish\|schedule` | Publish now / schedule; SSE progress per publish job |
| `GET /api/distribution/oauth/{platform}/start\|callback` | OAuth connect flow (BYO or env apps) |
| `GET/POST/DELETE /api/vault/clips`, `GET /api/vault/quota` | Clip Vault |
| `POST /api/settings/clips/{clip_id}/feedback` | Explicit clip rating |
| `GET /api/health` | DB, Redis, storage, optional Ollama |
| `GET /api/meta` | content types, caption styles, reframe presets, emotions |
| `GET /metrics` | Prometheus (when enabled) |

### 7.2 SSE progress

`GET /api/jobs/{id}/progress` — events: `progress`, `done`, `error`.  
Supports `Last-Event-Id` replay via Redis seq counter (`backend/services/sse.py`).

### 7.3 Web UI

- Server Actions: `web/app/actions/jobs.ts`
- OpenAPI types: `web/lib/api/openapi.ts`
- Contextual legends: `web/lib/help/legends.ts` + `SectionLegend`, `LegendBadge`
- Auth panel: `web/components/auth/auth-panel.tsx` (httpOnly cookie)

**FigJam:** [UX journey](https://www.figma.com/board/q7QQNUwxaY75swD75WsCy9)

## 8. Security & auth

| Mode | Behavior |
|------|----------|
| Dev (`allow_anonymous: true`) | Jobs without `owner_id` visible to anonymous users |
| Prod | `allow_anonymous: false`, strong `STREAMCLIP_AUTH__SECRET_KEY` |
| Authenticated | JWT bearer; jobs scoped to `owner_id` |
| Quotas | `jobs_used_this_month` on create; minutes on `finalise_job` |
| Webhooks | HMAC-SHA256 body signature in `X-StreamClip-Signature` |
| Rate limit | Optional per-IP (`rate_limit.enabled`) |

**Implementation:** `backend/api/auth.py`, `backend/services/auth_service.py`, `backend/api/jobs.py`

## 9. Observability

### 9.1 Metrics (`/metrics`)

| Metric | Type | Labels |
|--------|------|--------|
| `streamclip_requests_total` | Counter | method, path, status |
| `streamclip_request_duration_seconds` | Histogram | method, path |
| `streamclip_active_jobs` | Gauge | — |
| `streamclip_celery_tasks_in_progress` | Gauge | — |
| `streamclip_jobs_completed_total` | Counter | status |
| `streamclip_clips_processed_total` | Counter | status |
| `streamclip_clip_render_seconds` | Histogram | — |
| `streamclip_pipeline_stage_seconds` | Histogram | stage (`ingest`, `transcribe`, `highlights`, `virality`) |
| `streamclip_webhook_deliveries_total` | Counter | result |

### 9.2 Logging & tracing

- structlog JSON when `log_json: true`
- Sentry when `observability.sentry_dsn` set (`backend/main.py`)
- OpenTelemetry OTLP when `otel_endpoint` set + SDK installed (`backend/observability.py`)
- Flower for Celery task inspection (dev)

### 9.3 SLO / performance targets

Performance is the primary constraint ([PERFORMANCE.md](PERFORMANCE.md)). The product runs on **one machine**, often CPU-only, so the desktop column is the one that matters for shipping. All levers already exist in `config/desktop.yaml`; the audit's job is to confirm they reach the frozen exe (F12) and fill real numbers via the desktop perf harness.

| SLI | Desktop GPU (product) | Desktop CPU (product) | Docker GPU (Pro) | Measurement |
|-----|-----------------------|-----------------------|------------------|-------------|
| Install → first clip | < 15 min (incl. 1.5 GB model DL) | < 45 min | n/a | Manual clean-VM gate |
| End-to-end job (5 clips, 1h) | < 15 min | < 60 min | < 15 min | `created_at` → `done` |
| `process_clip` p95 | < 90 s (NVENC) | < 10 min (libx264) | < 90 s | `streamclip_clip_render_seconds` |
| Sidecar boot → health | < 8 s (warm) | < 8 s | n/a | Electron health poll |
| Job completion | 95% reach `done` | 95% | 95% | `streamclip_jobs_completed_total{status="done"}` |

**Single-machine perf rules (must hold in `inprocess` mode, not just Celery):** long work off the request thread; GPU pool concurrency=1 (never oversubscribe a laptop GPU); idempotent `process_clip`; single full transcribe (`refine_clip_transcript: false` on desktop); discovery cap `target_clips × 6`.

## 10. Deployment (desktop — the product)

Build → sign → publish the installer. Guardrails exist to prevent the drift bugs; keep the order.

```powershell
# 1. Build the static UI (stashes middleware/app/api, restored in finally)
.\scripts\build_desktop_ui.ps1
# 2. Build the sidecar exe (PyInstaller; aborts if a critical ML pkg fails)
.\scripts\build_sidecar.ps1
# 3. Stage sidecar into Electron (FAILS if static/ui is newer than the exe — stale-UI guard F2)
.\scripts\stage_sidecar_for_electron.ps1
# 4. Build installer (electron-builder NSIS; afterPack validate-sidecar.js fails if no engine binary)
.\scripts\build_desktop_installer.ps1
# 5. Publish (asserts apps/desktop/package.json version == latest.yml — version-drift guard F3)
.\scripts\publish_desktop_release.ps1
```

**Ship gate (product):** [CLEAN_DESKTOP_VM_VERIFY.md](CLEAN_DESKTOP_VM_VERIFY.md) — automated pre-flight `scripts/verify_desktop_clean.ps1` **plus** the manual fresh-Windows-11 install → first clip. This, not `verify_coverage.ps1` alone, blocks a desktop release. See [DESKTOP_FAILURE_TAXONOMY.md](DESKTOP_FAILURE_TAXONOMY.md) for the classes it catches.

**Remaining ops:** EV Authenticode signing (F9, `packaging/installer/RELEASE_CHECKLIST.md`); macOS notarization.

*(Docker/compose deployment for the Pro SKU is in [Appendix D](#appendix-d--docker-self-host-runtime-dev--future-pro).)*

## 11. Known limitations

See **`docs/MASTER_TODO.md`** (open items) and **`docs/GAP_ANALYSIS.md`** (gap register). Beta-facing summary: **`docs/BETA_KNOWN_ISSUES.md`**.

| Item | Notes |
|------|-------|
| Playwright full e2e | Smoke gated on `E2E_RUN=1`; publish-flow extension — MASTER §3.3 |
| TikTok publish | Inbox upload implemented; direct-post requires `video.publish` scope audit — MASTER §2.1 |
| Publish analytics | No view/retention feedback loop — MASTER §2.16 |
| Speaker diarization | Not implemented — MASTER §2.18 |
| yt-dlp subs reuse | Downloaded but Whisper always runs — MASTER §2.19 |
| Instagram Reels | Not implemented — MASTER §2.22 |
| Coverage gate | Canonical measurement — MASTER §3.10; `scripts/verify_coverage.ps1` |

Full gap register: `docs/GAP_ANALYSIS.md`

## 12. Appendix

### 12.1 Reframe presets (`core/reframe.py`)

9 presets (`core/creator_options.py`): `fps_game`, `moba`, `battle_royale`, `sports_action`, `irl`, `podcast`, `presentation`, `cinematic_wide`, `auto`. Presets control subject tracking and HUD-safe cropping; the export frame is set separately by the job/clip `aspect_ratio` (9:16 default; also 1:1, 4:5, 16:9, 2:3 — see 12.1a). `MIN_SMOOTH_WINDOW_FRAMES = 60` floor regardless of preset.

### 12.1a Export aspect ratios (`core/creator_options.py`)

| Ratio | Resolution | Platforms |
|-------|------------|-----------|
| 9:16 | 1080×1920 | TikTok, YouTube Shorts, Instagram Reels, Snap Spotlight |
| 1:1 | 1080×1080 | Instagram Feed, X, LinkedIn, Facebook |
| 4:5 | 1080×1350 | Instagram Feed, Facebook Feed |
| 16:9 | 1920×1080 | YouTube, X, LinkedIn, Facebook |
| 2:3 | 1080×1620 | Pinterest |

Set per job (`CreateJobRequest.aspect_ratio`, snapshotted in `config_snapshot`) or overridden per clip (`render_overrides.aspect_ratio` via clip editor, triggers re-render). The reframe engine computes the largest target-AR crop window inside the HUD-safe band and falls back to a scale-only pass when the crop covers the full source frame. Splicing rejects clips with mismatched effective aspect ratios.

### 12.2 Caption styles (`core/creator_options.py`)

`gaming_impact`, `shorts_bold`, `tiktok_pop`, `karaoke_highlight`, `minimal_white`, `podcast_clean`, `accessibility_clean`, `none` (skip burn-in)

### 12.3 Webhook payload

```json
{
  "event": "job.completed",
  "job_id": "uuid",
  "status": "done",
  "clips_done": 5,
  "clips_failed": 0,
  "ts": 1719667200.0
}
```

Verify: `HMAC-SHA256(secret, raw_body)` compared to `X-StreamClip-Signature: sha256=...`

### 12.4 Module map

**FigJam:** [Module map](https://www.figma.com/board/8iN5c22ytkcwUNFhQtAMLc)

| Area | Path |
|------|------|
| Pipeline tasks | `core/tasks/pipeline_tasks.py` |
| Publish / vault tasks | `core/tasks/publish_tasks.py`, `core/tasks/vault_tasks.py` |
| Distribution | `core/distribution/` (service, oauth, youtube, tiktok, tokens, registry) |
| Vault | `core/vault/service.py` |
| Virality | `core/virality.py` |
| Creator options catalog | `core/creator_options.py` |
| Style learning | `core/style_learning.py`, `backend/services/feedback_service.py` |
| Captions | `core/captions.py`, `core/caption_timing.py` |
| FFmpeg helpers | `core/ffmpeg_utils.py` |
| Webhooks | `core/webhooks.py` |
| Metrics | `core/pipeline_metrics.py`, `backend/api/metrics.py` |

### 12.5 Skills

| Skill | Path |
|-------|------|
| Gap analysis | `.cursor/skills/streamclip-gap-analysis/` |
| Technical design | `.cursor/skills/streamclip-technical-design/` |

---

## Appendix C — Architecture decision: harden, don't rewrite

**Question the audit answered:** given the desktop app is buggy for other Windows users, do we harden the shared code, extract a desktop boundary, or rewrite?

| Option | New code | Reuse | Risk | Verdict |
|--------|----------|-------|------|---------|
| **A. Desktop-first harden** | Minimal (docs + a few edits) | ~100% of `core/` + seams | Low | **CHOSEN** |
| B. Extract desktop package boundary | Moderate (adapters) | High | Med | Fallback only if entanglement found |
| C. Greenfield rewrite | Massive | ~0% | High | **Rejected** |

**Evidence for A (from the Phase 0 code audit):** the pipeline and seams are mature and correct. The in-process worker already mirrors the Celery GPU/CPU split and invokes `on_failure` directly; the progress bus is a clean Redis-shaped shim; the GPU profile safely upgrades/downgrades; the writable-slot registry is complete; the Electron shell already has splash + error page + supervision. The **only** confirmed product-breaking code bug was the writable check being *log-only* instead of *fatal* — fixed in this revision as a ~10-line change. Everything else is verification-gate and documentation drift (F11), which is a process fix, not a code fix. Rewriting would discard a working ML pipeline (faster-whisper, ultralytics, librosa, captions, reframe, virality) to re-solve problems already solved — a direct violation of the performance-first and minimize-work constraints.

**Consequence:** treat the installer path as canonical for design, tests, and gates (this doc + [DESKTOP_FAILURE_TAXONOMY.md](DESKTOP_FAILURE_TAXONOMY.md) + [CLEAN_DESKTOP_VM_VERIFY.md](CLEAN_DESKTOP_VM_VERIFY.md)); keep `core/` shared; lift the desktop seam out of the coverage waiver.

### C.1 Premium self-host SKU (later — recommendation, not built)

The user ruled out raw `docker compose` as a product because CLI is too technical. For the future "run on my own GPU / team" tier:

| Option | Creator UX | Ops cost to us | Recommendation |
|--------|-----------|----------------|----------------|
| Raw `docker compose` | Poor (CLI) | Low | **Reject** as the pitch |
| One-click self-host wizard (Docker under the hood, zero CLI) | Good if wizard is excellent | Medium | Offer only if customers demand on-prem GPU |
| **Managed cloud we host** | Best (nothing to install) | Higher | **Lead with this** for seamless UX + recurring revenue |

**Recommended path:** desktop stays the free/local product; Pro = **managed cloud first**, with the one-click self-host wizard as a secondary option. The existing Docker stack becomes the *backend of the managed cloud*, not a thing we hand to customers. This reuses the entire `core/` + Celery path we already have (Appendix D) — no new pipeline work.

---

## Appendix D — Docker self-host runtime (dev / future Pro)

*This is the original Rev 1–4 architecture, retained verbatim for contributors and as the backend for the future managed-cloud/Pro SKU. It is **not** the shipped product.*

```
Browser → Next.js (3000) → FastAPI (8000) → Celery → Redis
                              ↓                    ↓
                           Postgres            MinIO, Ollama
Browser ← SSE progress ← Redis pub/sub
Browser ↔ MinIO (presigned PUT/GET)
```

**FigJam:** [System architecture](https://www.figma.com/board/t7Y1R2nOp1fl1Su1aNelxd)

### D.1 Services (docker-compose)

| Service | Port | Role |
|---------|------|------|
| web | 3000 | Next.js UI; rewrites `/api` to API in Docker dev |
| api | 8000 | FastAPI, job CRUD, auth, SSE relay, `/metrics` |
| worker | — | Celery: `default` + `gpu` queues |
| postgres | 5432 | Job/clip/user metadata |
| redis | 6379 | Broker, results, progress pub/sub |
| minio | 9000 | Object storage |
| ollama | 11434 | Local LLM (virality scoring) |
| flower | 5555 | Celery monitor (dev profile) |

### D.2 Request paths (Docker)

1. **URL job:** `POST /api/jobs` with `source_url` → worker ingests via yt-dlp → `jobs/{id}/source/source.mp4`.
2. **Upload job:** `POST /api/uploads/init` → browser PUT to MinIO (presigned) → `POST /api/jobs` with `source_upload_key`.
3. **Auth:** `POST /api/auth/register|login|refresh` → JWT; web stores httpOnly cookie + bearer in server actions.

### D.3 Deployment (Docker)

See `deploy/PRODUCTION.md`. GPU profile: `STREAMCLIP_EXPORT__CODEC=h264_nvenc`, `STREAMCLIP_WHISPER__DEVICE=cuda`. Rebuild after Python changes (`docker compose build api worker && docker compose up -d`). Verified via [CLEAN_VM_VERIFY.md](CLEAN_VM_VERIFY.md) — the **contributor/Pro** gate, distinct from the product gate.
