# StreamClip Gap Analysis

**Last run:** 2026-06-29 (revision 3b — creator UX + post-gen actions)

## Executive summary

StreamClip targets **all creator verticals** with content profiles and hybrid peak discovery. This pass adds **bulk ZIP download**, **single-clip re-render**, **richer clip cards** (transcript, virality reason, copy link), and **discovery efficiency** caps. Remaining mastery work: trim editor, splice, asset vault, social publish.

**New this run:** T28–T32 (peak discovery, profiles, meme_keywords, meta/UI wiring). README corrected (virality is post-hoc, not discovery).

## Technical gaps

| ID | Claim | Status | Sev | Evidence |
|----|-------|--------|-----|----------|
| T1 | SSE `Last-Event-Id` | **Fixed** | — | `backend/services/sse.py` |
| T2 | GPU queue separation | **Fixed** | — | `process_clip` → `gpu` |
| T3 | NVENC / `export.codec` | **Fixed** | — | `core/export_video.py` |
| T4 | YOLOv11 + ByteTrack | Implemented | — | `core/reframe.py` |
| T5 | Twitch chat spike | **Fixed** | — | `core/chat_spikes.py` |
| T6 | JWT auth routes | **Fixed** | — | `backend/api/auth.py` |
| T7 | `STREAMCLIP_PIPELINE__MODE` | **Fixed** | — | Removed from `.env.example` |
| T8 | `export.fps` min 60 | **Fixed** | — | `ExportConfig.fps` ge=60 |
| T9 | Anonymous job listing | **Fixed** | P2 | Owner scoping |
| T10 | Presigned public URLs | Implemented | — | `core/storage.py` |
| T11 | Modular ingest | Implemented | — | `core/ingest/` |
| T12 | Guaranteed clips | Implemented | — | `core/highlights.py` |
| T13 | Post-hoc virality | **Fixed** | — | `run_virality_scores` |
| T14–T27 | (prior pass) | **Fixed** | — | See revision 2 |
| T28 | Peak-based discovery | **Fixed** | P1 | `core/peak_detection.py`, `candidate_mode: hybrid` |
| T29 | Creator content profiles | **Fixed** | P1 | `core/content_profiles.py`, job snapshot |
| T30 | `meme_keywords` → overlays | **Fixed** | P1 | DB column + `update_virality`, `_clip_to_candidate` |
| T31 | README virality at discovery | **Fixed** | P2 | README updated — LLM is post-hoc |
| T32 | Score curve smoothing | **Fixed** | P2 | `smooth_series` before peak pick |
| T33 | Bulk clip ZIP export | **Fixed** | — | `GET /api/jobs/{id}/clips.zip` |
| T34 | Single-clip regenerate | **Fixed** | P1 | `POST …/regenerate`, `process_clip(force=True)` |
| T35 | Discovery candidate cap | **Fixed** | P2 | Top `target_clips × 6` pre-NMS |
| T36 | Per-stage Prometheus histograms | **Fixed** | P2 | `streamclip_pipeline_stage_seconds` in `pipeline_tasks.py` |
| T37 | Docker dev source mounts | **Fixed** | P0 | `docker-compose.yml` mounts `backend/`, `core/`, `tests/` |
| T38 | bcrypt/passlib auth hashing | **Fixed** | P0 | Direct `bcrypt` in `backend/middleware/auth.py` |
| T39 | Parallel virality LLM scoring | **Fixed** | P1 | `score_clips_virality_parallel` + `llm.parallel_workers` |

## UX gaps

| ID | Journey / control | Status | Sev | Evidence |
|----|-------------------|--------|-----|----------|
| U1 | Tooltips / legends | **Fixed** | — | `web/lib/help/legends.ts` |
| U2 | Create job form | **Fixed** | — | Content type + all API fields |
| U3 | SSE progress errors | **Fixed** | — | `live-progress.tsx` |
| U4 | Job error states | **Fixed** | — | Error boundary + legends |
| U5 | Playwright e2e | Partial | P2 | Health/meta; upload path open |
| U6 | API docs `/docs` | **Fixed** | — | `next.config.mjs` |
| U7 | Cancel job UI | **Fixed** | — | `CancelJobButton` |
| U8 | Auth UI | **Fixed** | — | `AuthPanel` |
| U9 | Clip overlay visibility | **Fixed** | P2 | Overlay chips on `ClipCard` |
| U10 | `/api/meta` in UI | Partial | P2 | Profiles in form; presets still local |
| U11 | Post-gen clip actions | **Partial** | P1 | Single-clip regenerate + ZIP export; trim editor open |
| U12 | Transcript panel on clip | **Fixed** | — | Expandable transcript + virality reason on card |

## Creator-platform gaps (mastery trajectory)

| ID | Capability | Status | Priority |
|----|------------|--------|----------|
| C1 | Multi-vertical profiles | **Shipped** | — |
| C2 | Peak + chat discovery | **Shipped** | — |
| C3 | Post-gen editor (trim, restyle) | Roadmap | P1 |
| C4 | Splice / merge clips | Roadmap | P1 |
| C5 | Asset vault API | Roadmap | P2 |
| C6 | Social publish | Roadmap | P3 |
| C7 | Batch ZIP export | Roadmap | P2 |
| C8 | Per-clip webhooks | Roadmap | P2 |
| C9 | Channel style learning | Research | P3 |

## Resolved since revision 2

- T28 — Hybrid peak discovery (`segments` \| `peaks` \| `hybrid`)
- T29 — Content profiles: gaming, irl, podcast, esports, general
- T30 — `meme_keywords` persisted (migration `0002_clip_meme_keywords`)
- U9 — Overlay keywords shown on clip cards
- U2 — Content type selector on create job

## Intentional deferrals (roadmap)

- Speaker diarization
- Direct social publish (YouTube Shorts / TikTok / Reels)
- User-uploaded asset vault API
- Stripe billing / tier enforcement
- Full Playwright upload → clips e2e
- yt-dlp subtitle reuse for Whisper
- Deep learning highlight models (autoencoder / DENAN) — CPU-practical signals preferred
- Face-cam reaction signal (S5 from research proposal)

## Verification commands

```bash
# Unit tests (no full conftest chain)
python -c "..."  # see tests/test_peak_detection.py

# Full stack
docker compose build api worker && docker compose up -d
docker compose exec api alembic upgrade head
```

## How to re-run

Invoke skill: **`streamclip-gap-analysis`** (`.cursor/skills/streamclip-gap-analysis/SKILL.md`)

See also: `docs/CREATOR_PLATFORM.md`, `docs/TECHNICAL_DESIGN.md`
