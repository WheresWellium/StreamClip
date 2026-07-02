# StreamClip Gap Analysis

**Last run:** 2026-07-01 (revision 4 — modularity + distribution audit)

## Executive summary

The **clip pipeline and distribution plane are production-shaped**: modular `core/` services, registry-based platforms, and a clean web stack (actions → `distributionApi` → `DistributionService`). The largest gaps are **stale documentation** (prior register still listed social publish and asset vault as roadmap) and **minor API surface duplication** (job-scoped vs hub-scoped publish endpoints). **No Vercel AI SDK** — LLM uses native Ollama/OpenAI/Anthropic clients in Python; migration is not warranted.

## Technical gaps

| ID | Claim | Status | Sev | Fix | Evidence |
|----|-------|--------|-----|-----|----------|
| T1–T39 | (prior revisions) | **Fixed** | — | — | See revision 3b |
| T40 | Social distribution shipped | **Fixed** | P1 | doc | `core/distribution/`, `backend/api/distribution.py`, `web/app/distribution/` |
| T41 | Clip Vault shipped | **Fixed** | P1 | doc | `core/vault/service.py`, `backend/api/vault.py`, `/vault` |
| T42 | Asset vault API | **Implemented** | P2 | doc | `backend/api/assets.py` — list/create/delete; embedding UI open |
| T43 | `.env.example` distribution keys | **Fixed** | P1 | code | `STREAMCLIP_DISTRIBUTION__*` added to `.env.example` |
| T44 | `schemas.py` publish stub label | **Fixed** | P2 | code | Comment updated — publish is live, TikTok upload stubbed by flag |
| T45 | Celery `vault_tasks` routing | **Fixed** | P2 | code | Explicit `core.tasks.vault_tasks.*` → `default` in `celery_app.py` |
| T46 | Dead `jobsApi.publishClip` client | **Fixed** | P2 | code | Removed from `web/lib/api/client.ts`; web uses `distributionApi.publish` |
| T47 | `PRODUCTION.md` distribution env | **Fixed** | P1 | doc | `deploy/PRODUCTION.md` §1.3 now lists `STREAMCLIP_DISTRIBUTION__*` + links the runbook |
| T48 | README roadmap stale | **Fixed** | P1 | doc | README roadmap updated for vault, publish, webhooks |
| T49 | Job-scoped publish API overlap | Partial | P2 | defer | `POST /api/jobs/{id}/clips/{id}/publish` duplicates hub `POST /api/distribution/publish`; batch-publish still job-scoped |
| T50 | TikTok upload | **Fixed** | P2 | code | Inbox-flow upload implemented (`upload_video_file`); flag off pending TikTok app approval |
| T51 | Stripe billing | **Removed** | P2 | code | Lemon Squeezy is the sole provider; license chain wired end-to-end (see MASTER_TODO 2a) |
| T52 | OpenAPI type drift | **Fixed** | P2 | code | `web/lib/api/openapi.ts` regenerated; `approval_status` literal union from backend schema |

## UX gaps

| ID | Journey / control | Status | Sev | Fix | Evidence |
|----|-------------------|--------|-----|-----|----------|
| U1–U12 | (prior revisions) | Mostly **Fixed** | — | — | See revision 3b |
| U13 | Distribution journeys | **Implemented** | — | — | `clip-destinations-drawer.tsx`, `vault-destinations-drawer.tsx`, `/distribution` |
| U14 | Pro gate messaging | **Fixed** | P2 | code | `requireDistributionSession()` in `web/lib/distribution/access.ts` |
| U15 | Asset vault UI | Partial | P2 | defer | API exists; no dedicated `/assets` management page |
| U16 | Playwright full upload e2e | Partial | P2 | defer | `web/package.json` `test:e2e`; smoke only |

## Modularity & duplication register

| Area | Finding | Severity | Recommendation |
|------|---------|----------|----------------|
| Publish routing | Two entry points: `jobs.py` (`publish_clip`, `batch_publish`) and `distribution.py` (`publish`, `schedule`) — both delegate to `DistributionService` | P2 | Keep batch on jobs router; consider deprecating single-clip jobs publish (unused by web) |
| Schedule endpoint | `POST /schedule` is thin wrapper over `publish_now(..., scheduled_at=...)` | OK | Intentional REST surface for schedule UX |
| Web auth pattern | Repeated `getAccessToken` + `hasDistributionAccess` in actions | **Fixed** | `requireDistributionSession()` helper |
| Skills overlap | `streamclip` (comprehensive) vs `streamclip-development` (quick-start index) vs `streamclip-social-distribution` | OK | Hierarchy intentional; development skill points to siblings |
| `core/` vs `backend/` | Pipeline + distribution in `core/`; HTTP + repos in `backend/` | OK | Matches skill conventions; Celery uses `backend.db.session` |
| Platform extension | `core/distribution/registry.py` + adapter pattern (`youtube.py`, `tiktok.py`) | OK | Add Instagram via new adapter + `PLATFORMS_V1` entry |
| Inline import | `core/vault/service.py` lazy-imports `copy_clip_to_vault` | P2 | Documented circular-dep avoidance; acceptable |

## Creator-platform gaps (mastery trajectory)

| ID | Capability | Status | Priority |
|----|------------|--------|----------|
| C1 | Multi-vertical profiles | **Shipped** | — |
| C2 | Peak + chat discovery | **Shipped** | — |
| C3 | Post-gen editor (trim, restyle) | **Shipped** | — | `web/components/clips/clip-editor.tsx` — trim, reframe, captions, aspect ratio per clip |
| C4 | Splice / merge clips | Partial | P1 | `jobs.py` splice endpoint exists |
| C5 | Asset vault API | **Shipped** | — | UI management open |
| C6 | Social publish | **Shipped** | — | YouTube live; TikTok flag-gated |
| C7 | Batch ZIP export | **Shipped** | — | T33 |
| C8 | Per-clip webhooks | **Shipped** | — | `deliver_clip_webhook` in `core/tasks/pipeline_tasks.py` |
| C9 | Channel style learning | **Shipped** | — | `core/style_learning.py` implemented + wired |

## AI / LLM layer assessment

| Item | Status |
|------|--------|
| Vercel AI SDK (`ai` package) | **Not used** — `web/package.json` has no `ai` dependency |
| Python LLM | `core/virality.py` — native `ollama`, `openai`, `anthropic` clients via `_build_client()` |
| Discovery vs post-hoc | Correct: `core/highlights.py` sets `llm_virality=0.0` at discovery; `run_virality_scores` + `ensemble_with_virality()` post-hoc |
| AI SDK migration | **Not recommended** — Python pipeline owns LLM; no streaming chat UI; migration adds dep without clear win |

## Resolved since revision 3b (2026-07-01)

- T40–T48 — Documentation and modularity fixes from modularity audit
- T45 — Explicit Celery route for `vault_tasks`
- T46 — Removed dead `jobsApi.publishClip` client method
- U14 — Consolidated distribution Pro gate via `requireDistributionSession()`

## Intentional deferrals (roadmap)

- Speaker diarization
- Instagram Reels platform adapter
- TikTok live upload (Content Posting API + flag)
- Stripe billing enforcement
- Full Playwright upload → clips e2e
- yt-dlp subtitle reuse for Whisper
- Deprecate `POST /api/jobs/{id}/clips/{clip_id}/publish` after API consumers migrate to hub
- Asset vault management UI page
- Deep learning highlight models (autoencoder / DENAN)

## Verification commands

```bash
python -c "from backend.main import app"
cd web && npm run build
pytest tests/test_celery_publish.py tests/test_publish_notify.py -q
```

## How to re-run

Invoke skill: **`streamclip-gap-analysis`** (`.cursor/skills/streamclip-gap-analysis/SKILL.md`)

See also: `docs/CREATOR_PLATFORM.md`, `docs/TECHNICAL_DESIGN.md`, `docs/distribution-runbook.md`
