# StreamClip — Technical Design

**Revision:** 3 (2026-06-29)  
**Status:** Active

## 1. Purpose & scope

StreamClip is a self-hosted pipeline that ingests long-form video (gaming, IRL, podcast, esports), detects highlights, scores virality post-hoc, and renders vertical (9:16) clips with reframing, karaoke captions, and optional meme overlays.

**In scope:** ingest, transcription, highlight discovery, post-hoc virality, per-clip render, JWT auth API, web UI with contextual legends, REST API, Docker deployment, Prometheus metrics, optional webhooks.  
**Out of scope (roadmap):** social publishing, Stripe billing, speaker diarization, user asset vault API.

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
| web | 3000 | Next.js UI; rewrites `/api`, `/docs` to API |
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

**Content profiles** (`core/content_profiles.py`): per-job `content_profile` tunes weights for gaming, IRL, podcast, esports, general.

- NMS + boundary snap to word edges when transcript available
- `_guaranteed_clips()` ensures clip rows always exist

### 4.3b Virality scoring (`core/virality.py`)

Post-hoc LLM metric on finished clip transcripts — **never gates clip creation**.

1. `run_virality_scores` runs after highlights, before render fan-out
2. `score_clip_virality()` → JSON: score 0–100, emotion, meme_keywords
3. `ensemble_with_virality()` recomputes rank using profile or `highlight.weight_*`; `meme_keywords` persisted on `Clip` for overlay matching
4. Clips reranked by `ensemble_score` before `fan_out_clips`

**LLM providers:** `ollama` (default), `openai`, `anthropic` — `core/virality.py::_build_client`

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
| `User` | email, hashed password, `jobs_used_this_month`, `minutes_processed_this_month` |
| `Job` | `owner_id`, status, stage, progress, `config_snapshot`, storage keys |
| `Clip` | start/end, scores (`audio`, `spectral`, `flow`, `llm`, `ensemble`), emotion, storage keys |
| `Asset` | schema present; vault API not implemented |

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
| `POST /api/jobs` | Create job (URL or upload key) |
| `GET /api/jobs`, `GET /api/jobs/{id}` | List/detail; owner-scoped when auth enabled |
| `POST /api/jobs/{id}/cancel` | Cancel in-flight job |
| `POST /api/uploads/init` | Presigned PUT URL |
| `POST /api/auth/register\|login\|refresh` | JWT issuance |
| `GET /api/auth/me` | Current user |
| `GET /api/health` | DB, Redis, storage, optional Ollama |
| `GET /api/meta` | caption styles, reframe presets, emotions |
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

| Item | Notes |
|------|-------|
| Playwright full e2e | Config exists; happy path gated on `E2E_RUN=1` |
| Asset vault API | `Asset` model only; overlays use filesystem manifest |
| Stripe / tier enforcement | Quota counters exist; no payment integration |
| Social publish | Manual download from UI |
| Speaker diarization | Not implemented |
| yt-dlp subs reuse | Downloaded but Whisper always runs on audio |
| `/api/meta` in UI | Presets also hardcoded in create-job form |

Full gap register: `docs/GAP_ANALYSIS.md`

## 12. Appendix

### 12.1 Reframe presets (`core/reframe.py`)

| Preset | smooth_window (≥60) | Best for |
|--------|---------------------|----------|
| fps_game | 60 | FPS titles |
| moba | 60 | MOBA |
| battle_royale | 60 | BR |
| irl / podcast | 90 | Talking head |

### 12.2 Caption styles

`gaming_impact`, `tiktok_pop`, `minimal_white`, `podcast_clean`

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
| Virality | `core/virality.py` |
| Captions | `core/captions.py`, `core/caption_timing.py` |
| FFmpeg helpers | `core/ffmpeg_utils.py` |
| Webhooks | `core/webhooks.py` |
| Metrics | `core/pipeline_metrics.py`, `backend/api/metrics.py` |

### 12.5 Skills

| Skill | Path |
|-------|------|
| Gap analysis | `.cursor/skills/streamclip-gap-analysis/` |
| Technical design | `.cursor/skills/streamclip-technical-design/` |
