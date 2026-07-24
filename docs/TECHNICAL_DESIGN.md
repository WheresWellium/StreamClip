# StreamClip — Technical Design

**Revision:** 4 (2026-07-01)  
**Status:** Active

## 1. Purpose & scope

StreamClip is a self-hosted pipeline that ingests long-form video (gaming, IRL, podcast, esports, and more), detects highlights, scores virality post-hoc, and renders social-ready clips (9:16 default; 1:1, 4:5, 16:9, 2:3 selectable) with reframing, karaoke captions, and optional meme overlays — then distributes them to YouTube and TikTok.

**In scope:** ingest, transcription, highlight discovery, post-hoc virality (profile-aware, context-enriched), per-clip render, JWT auth API, web UI with contextual legends, REST API, Docker deployment, Prometheus metrics, optional webhooks, **social distribution** (YouTube publish, TikTok OAuth, scheduling, Clip Vault), style learning from explicit + implicit feedback.  
**Out of scope (roadmap):** speaker diarization, TikTok direct-post (inbox upload shipped behind `TIKTOK_PUBLISH_ENABLED`, default off pending TikTok app approval; direct public posting needs the `video.publish` scope audit), Instagram Reels, multi-aspect export (1:1 / 16:9). Billing is Lemon Squeezy (license keys); Stripe was dropped.

## 2. Goals & non-goals

| Goal | Non-goal |
|------|----------|
| **Wall-clock throughput** — fastest path from URL to finished clips | Feature breadth without perf budget |
| Browser-direct MinIO uploads | Proxying video through API |
| Tier-aware fast ingest for clips | Real-time streaming edit |
| Guaranteed clip output (always N clips) | Virality gating clip creation |
| Post-hoc virality for ranking & splice UX | Perfect LLM accuracy on first pass |
| Word-level caption sync on rendered clips | Generic subtitle burn without re-transcribe |
| Local LLM via Ollama (OpenAI/Anthropic optional) | Mandatory cloud APIs |
| Idempotent clip render (skip if done) | Re-running full pipeline on retry |
| Signed webhooks on job completion | Built-in Zapier/IFTTT connectors |

## 3. Runtime architecture

```
Browser → Next.js (3000) → FastAPI (8000) → Celery → Redis
                              ↓                    ↓
                           Postgres            MinIO, Ollama
Browser ← SSE progress ← Redis pub/sub
Browser ↔ MinIO (presigned PUT/GET)
```

**FigJam:** [System architecture](https://www.figma.com/board/t7Y1R2nOp1fl1Su1aNelxd)

### 3.1 Services (docker-compose)

| Service | Port | Role |
|---------|------|------|
| web | 3000 | Next.js UI; rewrites `/api` to API in Docker dev; **no** `/docs` proxy in external/desktop builds |
| api | 8000 | FastAPI, job CRUD, auth, SSE relay, `/metrics` |
| worker | — | Celery: `default` + `gpu` queues |
| postgres | 5432 | Job/clip/user metadata |
| redis | 6379 | Broker, results, progress pub/sub |
| minio | 9000 | Object storage |
| ollama | 11434 | Local LLM (virality scoring) |
| flower | 5555 | Celery monitor (dev profile) |

### 3.2 Request paths

1. **URL job:** `POST /api/jobs` with `source_url` → worker ingests via yt-dlp → `jobs/{id}/source/source.mp4`
2. **Upload job:** `POST /api/uploads/init` → browser PUT to MinIO → `POST /api/jobs` with `source_upload_key`
3. **Auth (optional):** `POST /api/auth/register|login|refresh` → JWT; web stores httpOnly cookie + bearer in server actions

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

### 9.3 SLO targets (self-hosted reference)

| SLI | Target | Measurement |
|-----|--------|-------------|
| API availability | 99.5% | `/api/health` status=ok |
| Job completion | 95% of jobs reach `done` | `streamclip_jobs_completed_total{status="done"}` |
| Clip render p95 | <10 min/clip (CPU medium) | `streamclip_clip_render_seconds` |
| Caption word sync | subjective QA | re-transcribe + karaoke path |

## 10. Deployment

See `deploy/PRODUCTION.md`. GPU profile: `STREAMCLIP_EXPORT__CODEC=h264_nvenc`, `STREAMCLIP_WHISPER__DEVICE=cuda`.

**Rebuild after Python changes** (code baked into images):

```powershell
docker compose build api worker
docker compose up -d
```

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
