# StreamClip — Creator Platform Vision

**Status:** Active (2026-06-29)  
**Audience:** Product, engineering, creators evaluating self-hosted clip tooling

## Mission

Give **every content creator** — gamers, IRL streamers, podcasters, educators, esports broadcasters — a **self-hosted, mastery-level** path from long-form video to publish-ready vertical clips, without subscriptions, watermarks, or opaque cloud black boxes.

## Who we serve

| Creator vertical | Primary signals | StreamClip today |
|------------------|-----------------|------------------|
| Twitch / YouTube gaming | Chat spikes, motion, audio peaks | `content_profile: gaming`, hybrid peak discovery |
| IRL / Just Chatting | Dialogue energy, reactions | `content_profile: irl` |
| Podcast / interview | Speech peaks, minimal motion | `content_profile: podcast` |
| Esports / casted | Caster audio + action + chat | `content_profile: esports` |
| Mixed / general | Balanced ensemble | `content_profile: general` |

## Mastery principles

1. **Always ship clips** — guaranteed fallback; virality never gates output.
2. **Evidence-based discovery** — peak detection + multimodal scoring (research-aligned).
3. **Creator-owned data** — self-hosted MinIO, Postgres, optional local LLM.
4. **Transparent scores** — UI legends explain every metric and pipeline stage.
5. **Frozen job config** — reproducible renders via `config_snapshot`.
6. **Post-hoc intelligence** — LLM ranks and labels after clips exist (splice-ready).
7. **Production operability** — metrics, webhooks, retention, auth, health probes.

## Platform layers

```
┌─────────────────────────────────────────────────────────┐
│  Creator UI (Next.js) — jobs, progress, clips, auth   │
├─────────────────────────────────────────────────────────┤
│  API (FastAPI) — jobs, uploads, meta, SSE, webhooks    │
├─────────────────────────────────────────────────────────┤
│  Pipeline (Celery) — ingest → transcribe → discover →   │
│    virality → render (reframe, caption, overlay)      │
├─────────────────────────────────────────────────────────┤
│  Intelligence — peaks, profiles, Whisper, Ollama, YOLO  │
├─────────────────────────────────────────────────────────┤
│  Data — Postgres, MinIO, Redis                        │
└─────────────────────────────────────────────────────────┘
```

## Roadmap (world-class trajectory)

### Now (shipped)

- Hybrid peak + transcript highlight discovery
- Content profiles with tuned signal weights + recommended reframe/caption presets
- Post-hoc virality + meme keyword persistence → overlays
- Word-synced captions, idempotent render, webhooks (job + per-clip), metrics
- Post-generation clip editor (trim, restyle, regenerate, aspect ratio)
- `/api/meta` drives the create-job UI end to end
- Asset vault end-to-end: API + management UI (`/settings/assets`) + overlay engine reads `Asset` DB rows
- Batch export ZIP; multi-aspect export (9:16, 1:1, 4:5, 16:9, 2:3)
- Desktop embedded runtime seam (ADR-001 §4.1–4.5): SQLite profile, in-process queue, local storage HTTP, bundled ffmpeg resolution; sidecar + static UI scaffolds
- Social publish: YouTube Shorts live; TikTok inbox upload flag-gated
- Channel-style learning from creator feedback (`core/style_learning.py`)
- Licensing/commerce via Lemon Squeezy (Stripe removed)

### Next (high value)

- E2E publish flow tests (Playwright)
- Desktop packaging: Server Actions → API migration for static export, full PyInstaller bundle, Electron sidecar shell (see `docs/MASTER_TODO.md` §4.6–4.13)

### Later (scale & distribution)

- Instagram Reels adapter
- Publish performance feedback loop (YouTube Analytics → style learning)
- Live stream / OBS integration
- Speaker diarization

## Success metrics

| Metric | Target |
|--------|--------|
| Clip yield on quiet VODs | ≥ 1 clip (guaranteed path) |
| Discovery precision (subjective QA) | Top-3 clips feel “shareable” on gaming VODs |
| Caption sync | Words align within ~200ms on re-transcribed clips |
| Time-to-first-clip (1h VOD, CPU) | < 15 min median |
| Creator comprehension | No support doc needed for create → download flow |

## Related docs

- `docs/TECHNICAL_DESIGN.md` — implementer reference
- `docs/GAP_ANALYSIS.md` — living gap register
- `deploy/PRODUCTION.md` — self-hosted deployment
