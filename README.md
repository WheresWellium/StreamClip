# StreamClip

**Self-hosted, zero-subscription AI clip pipeline.**
From a 5-hour Twitch VOD to 5 ready-to-post vertical clips — in minutes.
No watermarks. No tokens. No Eklipse.

---

## What's in the box

| Layer | Stack | Why |
|---|---|---|
| Frontend | Next.js 15 (App Router, RSC, Server Actions) | Server-streamed UI, no client-side data waterfall, instant route-level code splitting |
| API | FastAPI (async Python) | One deployment for both the API and the ML pipeline — no microservice tax |
| Queue | Celery + Redis | Per-stage retries, GPU/CPU queue separation, crash recovery |
| Database | PostgreSQL (SQLAlchemy 2.0 async + Alembic) | Job/clip metadata, full transactional model |
| Storage | MinIO (S3-compatible) | Browser uploads bytes directly via presigned PUT; the API never proxies media |
| Realtime | Server-Sent Events | One-way progress works through every proxy, auto-reconnects via `Last-Event-Id` |
| LLM | Ollama + llama3.2 (local) | No API costs; pluggable to OpenAI/Anthropic via env vars |

---

## Pipeline modules

- **Highlight detection** — hybrid peak + transcript discovery: audio energy, spectral novelty, optical flow, Twitch chat spikes; content profiles per vertical; greedy NMS and word-boundary snapping. Post-hoc LLM virality ranks clips after creation.
- **Speech-to-text** — `faster-whisper` with gaming hot-word boosting and word-level timestamps.
- **Vertical reframe (9:16)** — YOLOv11 + ByteTrack subject tracking, two-pass Gaussian-smoothed camera path with velocity clamping, HUD-protection zones per genre preset.
- **Animated captions** — ASS format with pop-in animations, gaming-term emphasis flashes, pause-aware word grouping, emoji injection.
- **Semantic meme overlays** — `sentence-transformers` (`all-MiniLM-L6-v2`, ~90MB local) matches asset descriptions to clip hooks by cosine similarity. SFX muxed at the audio peak frame via librosa.
- **NVENC export** — H.264 via `export.codec` (`libx264` CPU default, `h264_nvenc` on GPU worker), CRF/CQ 17, min 60fps, 1080×1920.

---

## Quick start

### Prerequisites

- Docker + Docker Compose
- Optional: NVIDIA GPU + Container Toolkit for the `gpu-worker` service
- ~10 GB free disk for models on first run

### One command

```bash
git clone https://github.com/yourname/streamclip.git
cd streamclip
docker compose up --build
```

That spins up the full stack:

| Service | Port | URL |
|---|---|---|
| Next.js web | 3000 | http://localhost:3000 |
| FastAPI | 8000 | http://localhost:8000/docs |
| MinIO console | 9001 | http://localhost:9001 (user: `streamclip` / pass: `streamclip_secret`) |
| Postgres | 5432 | — |
| Redis | 6379 | — |
| Ollama | 11434 | — |
| Flower (Celery UI) | 5555 | — (run separately with `--profile dev`) |

First boot pulls the llama3.2 model (~2GB) — give it a minute.

### Local dev without Docker

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Bring up just the infra
docker compose up postgres redis minio minio-init ollama -d

# Run migrations
alembic upgrade head

# API
uvicorn backend.main:app --reload

# Celery workers (in separate terminals)
celery -A core.celery_app.celery_app worker -Q default -l info
celery -A core.celery_app.celery_app worker -Q gpu -l info --concurrency=1

# Frontend
cd web && npm install && npm run dev
```

---

## Architecture

```
Browser
   │
   ▼
Next.js 15 (RSC + Server Actions + SSE client)
   │             ▲
   │             │ progress stream
   │             │
   ▼             │
FastAPI ── enqueue ──▶ Redis ──▶ Celery workers
   │                                 │
   │ presigned URL                   │ uses
   ▼                                 ▼
MinIO ◀──── upload / download ──── Pipeline
                                  (ingest → transcribe →
                                   highlights → reframe →
                                   caption → overlay → export)
   ▲                                 │
   │                                 │ publishes progress
   │                                 ▼
   └────── reads metadata ────── Postgres
                                     ▲
                                     │
                                     │ subscribes
                                     │
                                  Redis pub/sub ──▶ SSE relay ──▶ Browser
```

Why this shape:

- **The browser never talks to MinIO through the API.** Uploads use presigned PUT URLs; downloads use presigned GET URLs. The FastAPI process is never a bottleneck for media bytes.
- **Long-running work is queued, never inline.** A 5-hour VOD takes ~10 minutes to process; that can't live inside a request handler. Celery + Redis own it.
- **The GPU has its own queue.** Heavy stages (transcribe, reframe, overlay) route to the `gpu` queue with `concurrency=1`. Cheaper stages route to `default` at `concurrency=4`. The GPU never sits idle waiting for an LLM call.
- **Progress streams via SSE.** One-way server→client updates are a perfect fit. EventSource auto-reconnects via `Last-Event-Id`, so a network blip doesn't blank-screen the UI.

---

## Project layout

```
streamclip/
├── core/                       # The pipeline (no web framework dependencies)
│   ├── config.py               # Pydantic v2 settings (YAML + env var)
│   ├── models.py               # Frozen dataclasses (Transcript, ClipCandidate, …)
│   ├── errors.py               # Domain exception hierarchy with HTTP mapping
│   ├── storage.py              # Storage ABC (local / S3 / MinIO) + presigned URLs
│   ├── ingest.py               # yt-dlp + ffprobe + hash-based caching
│   ├── transcribe.py           # faster-whisper with gaming hot-words
│   ├── highlights.py           # Multi-signal ensemble + NMS + boundary snap
│   ├── reframe.py              # YOLOv11 + ByteTrack + smoothed camera path
│   ├── captions.py             # ASS animated captions
│   ├── overlay.py              # Semantic meme matcher + SFX injection
│   ├── celery_app.py           # Celery + Redis pub/sub progress publisher
│   └── tasks/
│       └── pipeline_tasks.py   # The Celery task chain
│
├── backend/                    # FastAPI gateway
│   ├── main.py                 # App factory + lifespan + middleware
│   ├── api/
│   │   ├── jobs.py             # POST/GET/DELETE /api/jobs + SSE progress
│   │   ├── uploads.py          # POST /api/uploads/init (presigned PUT)
│   │   ├── health.py           # /api/health + /api/meta
│   │   └── schemas.py          # Pydantic v2 wire models
│   ├── db/
│   │   ├── models.py           # SQLAlchemy 2.0 async ORM
│   │   ├── session.py          # Async engine + FastAPI dep
│   │   └── repositories.py     # JobRepository, ClipRepository, …
│   ├── services/
│   │   ├── job_service.py      # Business logic (job creation, DTOs)
│   │   └── sse.py              # Redis pub/sub → SSE relay
│   └── middleware/
│       ├── auth.py             # JWT + optional anonymous mode
│       └── rate_limit.py       # Redis sliding-window token bucket
│
├── web/                        # Next.js 15 frontend
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx            # Home: create form + jobs list (RSC)
│   │   ├── globals.css
│   │   ├── actions/jobs.ts     # Server Actions (createJob, cancelJob)
│   │   └── jobs/[id]/
│   │       ├── page.tsx        # Job detail (RSC + SSE upgrade)
│   │       ├── loading.tsx     # Streaming skeleton
│   │       ├── error.tsx
│   │       └── not-found.tsx
│   ├── components/
│   │   ├── jobs/
│   │   │   ├── create-job-form.tsx
│   │   │   ├── jobs-list.tsx
│   │   │   └── live-progress.tsx   # SSE-driven progress
│   │   ├── clips/clip-card.tsx
│   │   ├── upload/direct-upload.tsx # XHR → MinIO presigned PUT
│   │   └── ui/                      # Button, Card, Input, Badge, Progress
│   └── lib/
│       ├── api/
│       │   ├── client.ts            # Typed fetch wrapper + uploadFile helper
│       │   ├── types.ts             # Types matching FastAPI schemas
│       │   └── use-job-progress.ts  # EventSource hook
│       └── utils/format.ts
│
├── alembic/                    # DB migrations
│   ├── env.py
│   └── versions/
│       └── 0001_initial.py
│
├── assets/                     # Asset vault (gifs, stickers, sfx)
├── config.yaml                 # Default pipeline config
├── pipeline.py                 # CLI entry point
├── requirements.txt
├── docker-compose.yml          # Full stack one-command up
├── Dockerfile                  # Python API + worker
└── alembic.ini
```

---

## Usage

### Web UI

Open http://localhost:3000. Paste a Twitch/YouTube URL or upload a file. Watch the progress timeline. Download clips when they're done.

### CLI

```bash
# Twitch VOD → 5 clips
python pipeline.py "https://www.twitch.tv/videos/2345678901"

# Local file → 7 clips, battle-royale preset, watch progress
python pipeline.py ./recording.mp4 --clips 7 --preset battle_royale

# Skip progress tail (dispatch and exit)
python pipeline.py ./recording.mp4 --no-watch
```

### REST API

```bash
# Get an upload URL
curl -X POST http://localhost:8000/api/uploads/init \
  -H "Content-Type: application/json" \
  -d '{"filename": "stream.mp4", "content_type": "video/mp4"}'
# → { "upload_id": "...", "upload_url": "https://...", "storage_key": "uploads/..." }

# Upload directly to MinIO (no auth, no streaming through API)
curl -X PUT "$UPLOAD_URL" -H "Content-Type: video/mp4" --data-binary "@stream.mp4"

# Create a job referencing the upload
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source_upload_key": "uploads/...",
    "target_clips": 5,
    "caption_style": "gaming_impact",
    "reframe_preset": "fps_game"
  }'

# Stream progress
curl -N http://localhost:8000/api/jobs/JOB_ID/progress
```

---

## Configuration

Every value in `config.yaml` is overridable via env vars (prefixed `STREAMCLIP_`, nested with `__`):

```bash
STREAMCLIP_WHISPER__MODEL_SIZE=medium       # use medium instead of large-v3
STREAMCLIP_LLM__PROVIDER=openai             # switch to GPT-4o
STREAMCLIP_LLM__MODEL=gpt-4o-mini
STREAMCLIP_LLM__API_KEY=sk-...
STREAMCLIP_HIGHLIGHT__TARGET_CLIPS=10
STREAMCLIP_RATE_LIMIT__ENABLED=false        # disable rate limits locally
```

### Reframe presets

| Preset | YOLO confidence | Smoothing | Max pan speed | HUD reserve | Best for |
|---|---|---|---|---|---|
| `fps_game` | 0.45 | 60 frames (min) | 6%/frame | top 10% + bottom 18% | Valorant, CS, Apex |
| `moba` | 0.40 | 60 frames | 3%/frame | top 8% + bottom 22% | League, Dota |
| `battle_royale` | 0.45 | 60 frames | 8%/frame | top 8% + bottom 15% | Fortnite, Warzone |
| `irl` / `podcast` | 0.50 | 90 frames | 1–2%/frame | 0 | Talking head |
| `auto` | — | — | — | — | LLM picks preset from emotion |

### Caption styles

- `gaming_impact` — Impact font, uppercase, heavy outline, accent flash on gaming terms
- `tiktok_pop` — Bold round font, colour-animated, scale-bounce pop-in
- `minimal_white` — Clean Helvetica, thin outline
- `podcast_clean` — SF Pro Display, word-by-word reveal

---

## Performance

| Hardware | Per-clip render | Notes |
|---|---|---|
| RTX 3090 | 45–90 sec | NVENC encode, large-v3 Whisper, llama3.2 |
| RTX 3060 | 2–4 min | Same models |
| Apple M3 Max | 3–5 min | MPS acceleration; llama3.2 runs CPU-only |
| CPU only (Ryzen 9) | 10–20 min | Drop to `whisper.model_size: medium`, disable optical flow signal |

The optical-flow signal is the heaviest CPU cost. Set `highlight.weight_optical_flow: 0` and re-balance the remaining weights to sum to 1.0 for a ~2× speedup at the cost of one signal.

---

## Roadmap

- [x] Twitch chat-spike signal (`core/chat_spikes.py`, `core/twitch_chat.py`; requires `twitch_client_id` for live fetch)
- [ ] Speaker diarization for multi-streamer VODs (pyannote.audio integration)
- [ ] User-uploaded asset vault with embedding indexing
- [ ] Direct publish to YouTube Shorts / TikTok / Instagram Reels
- [ ] Multi-tenant billing tier (Stripe webhook hooked up; tier enum already in schema)
- [ ] Webhook notifications when jobs complete

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/TECHNICAL_DESIGN.md](docs/TECHNICAL_DESIGN.md) | Implementer-focused architecture |
| [docs/PERFORMANCE.md](docs/PERFORMANCE.md) | Performance doctrine, SLIs, hot-path map |
| [docs/GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md) | Doc vs code gap register |
| [docs/design/FIGMA_LINKS.md](docs/design/FIGMA_LINKS.md) | FigJam diagrams |

## Ship checklist

Before treating a build as production-ready:

1. `docker compose up -d --build` (rebuild bakes latest Python into images for prod)
2. `docker compose exec api alembic upgrade head`
3. `powershell -File scripts/verify_stack.ps1` — health + unit tests
4. Set `STREAMCLIP_AUTH__SECRET_KEY`, disable `allow_anonymous` for multi-user hosts
5. Optional GPU: `docker compose --profile gpu up -d`

**Dev note:** `docker-compose.yml` bind-mounts `backend/`, `core/`, and `tests/` so local Python changes apply without rebuild. Production deploys must use `--build` without relying on mounts.


MIT. Use it, fork it, sell your own subscription service on top — just don't pretend you invented the wheel.

*Built by people tired of paying for things they can run on their own GPU.*
