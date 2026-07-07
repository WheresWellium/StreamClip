---
name: streamclip-development
description: >-
  Quick-start guide for StreamClip development — repo map, stack, verification
  commands, and conventions. Use when implementing features, fixing bugs,
  onboarding to the repo, or any StreamClip task; load sibling skills for
  distribution, copy, ops, gap analysis, or technical design.
---

# StreamClip Development

## When to use

- **Any StreamClip work** — pipeline, API, web UI, auth, billing, deploy
- **Onboarding** — orient to repo layout and verification commands
- **Before large changes** — skim this skill, then load a focused sibling skill

## Product (one line)

**Long-form video → viral vertical shorts** (URL, upload, podcast, VOD — not streamers-only). Copy detail: [streamclip-copy-messaging](../streamclip-copy-messaging/SKILL.md).

## Repo map

| Path | Role |
|------|------|
| `backend/` | FastAPI app, routers, middleware, DB session |
| `core/` | Pipeline, distribution, vault, Celery tasks, config |
| `web/` | Next.js 15 App Router, components, server actions |
| `alembic/` | DB migrations (`alembic upgrade head`) |
| `docs/` | TDD, gap analysis, performance, distribution runbook |
| `deploy/` | Production compose, Caddy, GPU profiles |
| `tests/` | pytest (pipeline, distribution, celery) |

## Stack

| Layer | Tech |
|-------|------|
| Web | Next.js 15, RSC, Server Actions, Tailwind |
| API | FastAPI async, SQLAlchemy 2.0, Alembic |
| Queue | Celery + Redis (GPU + default queues) |
| DB | PostgreSQL |
| Storage | MinIO (presigned browser upload/download) |
| Progress | SSE via Redis pub/sub (`Last-Event-Id` reconnect) |
| LLM | Ollama default; OpenAI/Anthropic via env |

## Pipeline (clip creation)

```
start_pipeline → run_ingest → run_transcribe → run_highlights
  → run_virality_scores → fan_out_clips → process_clip × N → finalise_job
```

| Queue | Tasks |
|-------|-------|
| `gpu` | `run_transcribe`, `process_clip` |
| `default` | ingest, highlights, virality, fan-out, vault copy, publish |

Key modules: `core/tasks/pipeline_tasks.py`, `core/highlights.py`, `core/reframe.py`, `core/export_video.py`.

## Dev setup

```bash
docker compose up --build -d
docker compose exec api alembic upgrade head
cd web && npm install && npm run dev
```

See `CONTRIBUTING.md` for debugging Next.js, OpenAPI type regen, and Playwright.

## Long chat / summarization

When context compacts or the thread is summarized:

1. Read `docs/SESSION_STATE.md` first (rolling goal, blockers, next steps).
2. Read `AGENTS.md` for durable preferences and workspace facts.
3. Grep `agent-transcripts/<chat-id>/*.jsonl` for details — never read transcripts linearly.

Keep `SESSION_STATE.md` updated at phase boundaries (see `.cursor/rules/conversation-compaction.mdc`).

## Desktop profile (ADR-001, no Docker)

| Piece | Path / switch |
|-------|---------------|
| Config profile | `config/desktop.yaml` (or `STREAMCLIP_CONFIG=config/desktop.yaml`) |
| DB | SQLite via aiosqlite; portable types in `backend/db/types.py` |
| Queue | `STREAMCLIP_QUEUE__BACKEND=inprocess` → `core/inprocess_worker.py` |
| Storage | Local files served at `/storage/{key}` (`backend/api/local_storage.py`) |
| ffmpeg | `core/ffmpeg_bins.py` resolves `bin/ffmpeg/` then PATH |
| Sidecar | `python -m desktop_sidecar` → FastAPI on `127.0.0.1:8765` (migrations auto-run) |
| Static UI | `backend/static_ui.py` serves `static/ui/` when `web.serve_static: true` |

Verify scripts (PowerShell, from repo root): `scripts/verify_desktop.ps1` aggregates
`verify_desktop_db.ps1` + `verify_desktop_storage.ps1` + `verify_desktop_ffmpeg.ps1` +
sidecar/static tests; `scripts/verify_inprocess.ps1` needs Docker running.

## Verification commands

After backend changes:

```bash
python -c "from backend.main import app"
alembic upgrade head   # if models/migrations changed
pytest -q              # or targeted: pytest tests/test_celery_publish.py -q
```

After web changes:

```bash
cd web && npm run build
```

OpenAPI regen (after schema changes):

```bash
curl -s http://localhost:8000/openapi.json -o openapi.json
cd web && npx openapi-typescript ../openapi.json -o lib/api/openapi.ts && npm run typecheck
```

## Code conventions

1. **Minimal scope** — smallest correct diff; match surrounding style
2. **No inline imports** — top of module unless documented circular dep
3. **Exhaustive switch** — `never` in default for discriminated unions
4. **Toasts** — `useToastSafe` from `@/components/providers/toast-provider`; **not** `sonner`
5. **Celery DB** — `backend.db.session.db_session` in tasks (not `core.db`)
6. **Errors** — `StreamClipError` with `user_message` for API responses

## Web patterns

| Pattern | Location |
|---------|----------|
| Server actions | `web/app/actions/*.ts` — auth via `getAccessToken()` httpOnly cookies |
| API client | `web/lib/api/client.ts` — `jobsApi`, `distributionApi`, `vaultApi` |
| Types | `web/lib/api/types.ts` when OpenAPI lags; regen `openapi.ts` when stable |
| Help legends | `web/lib/help/legends.ts` |

## Implementation workflow

```
StreamClip task:
- [ ] Read affected modules (grep + read; don't assume)
- [ ] Match existing patterns (actions, repos, tasks)
- [ ] Implement minimal diff
- [ ] Verify import + build (+ tests if touched)
- [ ] Update docs if user-facing behavior changed
```

## Sibling skills (load when relevant)

| Skill | When |
|-------|------|
| [streamclip-social-distribution](../streamclip-social-distribution/SKILL.md) | Publish, schedule, vault, OAuth, queue UI |
| [streamclip-distribution-ops](../streamclip-distribution-ops/SKILL.md) | Celery, Beat, OAuth URIs, troubleshooting |
| [streamclip-copy-messaging](../streamclip-copy-messaging/SKILL.md) | Hero, onboarding, inclusive product copy |
| [streamclip-gap-analysis](../streamclip-gap-analysis/SKILL.md) | Doc/code drift, release audit |
| [streamclip-technical-design](../streamclip-technical-design/SKILL.md) | TDD, architecture docs |

## Key docs

| File | Role |
|------|------|
| `docs/TECHNICAL_DESIGN.md` | System design |
| `docs/GAP_ANALYSIS.md` | Known gaps |
| `docs/distribution-runbook.md` | Publish ops |
| `deploy/PRODUCTION.md` | Production deploy |

## Known limitations (honest)

- TikTok upload may be stubbed until Content Posting API is wired and flag enabled
- Instagram Reels not in v1 platform registry
- OpenAPI types may lag new distribution endpoints
- README still leans Twitch in places — product copy is broader (see copy skill)
