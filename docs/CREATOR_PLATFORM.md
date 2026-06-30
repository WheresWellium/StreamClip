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
- Content profiles with tuned signal weights
- Post-hoc virality + meme keyword persistence → overlays
- Word-synced captions, idempotent render, webhooks, metrics

### Next (high value)

- Post-generation clip actions (trim, restyle, regenerate)
- `/api/meta` fully drives create-job UI
- Asset vault API (replace filesystem-only overlays)
- Batch export ZIP, per-clip webhooks

### Later (scale & distribution)

- Social publish adapters (Shorts / TikTok / Reels OAuth)
- Channel-style learning from creator feedback
- Live stream / OBS integration
- Stripe tiers for hosted SaaS offering (optional)

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
