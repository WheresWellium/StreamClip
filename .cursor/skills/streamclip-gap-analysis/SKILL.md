---
name: streamclip-gap-analysis
description: >-
  Performs dual-track gap analysis on StreamClip — technical (code vs docs/config)
  and UX (UI vs user journeys). Produces a prioritized gap register with fixes.
  Use when auditing README accuracy, doc-code drift, UX completeness, production
  readiness, or when the user asks for gap analysis, doc vs reality, or UX audit.
---

# StreamClip Gap Analysis

## When to run

- Before releases or production bring-up
- After README / PRODUCTION.md / CONTRIBUTING changes
- When users report "docs say X but it doesn't work"
- After major refactors (ingest, pipeline, web UI)

## Outputs

1. **`docs/GAP_ANALYSIS.md`** — living register (update in place, date-stamp section)
2. Optional fixes — code for P0/P1, doc updates for intentional deferrals

**Publishing:** Gap registers are **internal-only**. Full exclude list is `exclude_docs` in `mkdocs.yml` (GAP/MASTER plus ops, commercial, design, demoted tutorials, etc.) — see `docs/INTERNAL.md`. Henna publishes only `docs/index.md` (download + how to use).

## Workflow

Copy and track:

```
Gap analysis progress:
- [ ] Phase 1: Inventory claims (docs)
- [ ] Phase 2: Technical verification (code)
- [ ] Phase 3: UX verification (web + journeys)
- [ ] Phase 4: Prioritize + write register
- [ ] Phase 5: Fix P0/P1 or document deferrals
```

### Phase 1 — Inventory claims

Read in order:

| Source | What to extract |
|--------|-----------------|
| `README.md` | Stack, pipeline stages, GPU queues, NVENC, SSE, presets, performance |
| `docs/PERFORMANCE.md` | SLIs, hot-path map, coding checklist, CPU/GPU profiles |
| `deploy/PRODUCTION.md` | Auth, Caddy routes, env vars, GPU profile |
| `CONTRIBUTING.md` | Test commands, dev setup |
| `config.yaml` + `.env.example` | Every key must exist in `core/config.py` |

Build a claim checklist (one row per verifiable statement).

### Phase 2 — Technical verification

For each claim, grep/read the implementation. Use this matrix:

| Area | Verify in |
|------|-----------|
| Ingest tiers | `core/ingest/`, `pipeline_tasks.run_ingest` |
| Transcript reuse | `load_job_transcript`, `run_highlights`, `process_clip` |
| Highlight scoring | `core/highlights.py` (threshold vs guaranteed clips) |
| Reframe presets | `core/reframe.py` PRESETS, `smooth_window >= 60` |
| Export codec/fps | `core/export_video.py`, ffmpeg call sites |
| Celery queues | `core/celery_app.py` task_routes vs actual task names |
| SSE | `backend/services/sse.py` (`id:` fields, `Last-Event-Id`) |
| Presigned URLs | `core/storage.py` `public_base_url` |
| Auth | `backend/middleware/auth.py`, routers in `backend/main.py` |
| API schemas | `backend/api/schemas.py` vs `web/lib/api/openapi.ts` |
| Performance / SLIs | `docs/PERFORMANCE.md`, `core/pipeline_metrics.py`, stage timers in `pipeline_tasks.py` |

**Severity**

| Level | Meaning |
|-------|---------|
| P0 | Broken in default docker-compose path |
| P1 | Documented feature missing or wrong behavior |
| P2 | Partial, stub, or dev-only limitation |

**Fix type**: `code` | `doc` | `both`

### Phase 3 — UX verification

Walk these journeys in code (or browser if stack is up):

1. **Create job** — URL and upload paths; tooltips on controls; form → API fields match
2. **Progress** — `LiveProgress` + SSE; errors surfaced; reconnect behavior
3. **Job detail** — clips grid, play, download, empty/error states
4. **Navigation** — `/docs` resolves; back links work
5. **A11y** — `aria-label`, focus rings on icon buttons

Check:

| File | UX concern |
|------|------------|
| `web/components/jobs/create-job-form.tsx` | All fields + help |
| `web/components/jobs/live-progress.tsx` | SSE error state |
| `web/components/clips/clip-card.tsx` | Play/download tooltips |
| `web/components/layout/header-nav.tsx` | API docs link |
| `web/app/jobs/[id]/error.tsx`, `not-found.tsx` | Recovery actions |

### Phase 4 — Write register

Use this template in `docs/GAP_ANALYSIS.md`:

```markdown
# StreamClip Gap Analysis

**Last run:** YYYY-MM-DD

## Executive summary
[2–3 sentences: biggest technical + UX gaps]

## Technical gaps

| ID | Claim | Status | Sev | Fix | Evidence |
|----|-------|--------|-----|-----|----------|

## UX gaps

| ID | Journey / control | Status | Sev | Fix | Evidence |
|----|-------------------|--------|-----|-----|----------|

## Resolved since last run
- [date] ID — what changed

## Intentional deferrals (roadmap)
- Twitch chat signal, diarization, etc.
```

### Phase 5 — Remediation rules

1. **P0/P1 technical** — implement minimal correct fix; don't expand scope
2. **Doc-only** — update README when behavior is intentionally limited
3. **UX P2** — tooltips, error copy, link fixes before new features
4. Never mark resolved without evidence (file:line or test)

## Quick grep pack

```bash
rg "libx264|h264_nvenc|cfg\.export" core/
rg "Last-Event-Id|event_id|id:" backend/ web/
rg "run_reframe|run_overlay|process_clip" core/celery_app.py
rg "allow_anonymous|get_for_owner" backend/
rg "tooltip|HelpTip" web/components/
```

## Cross-references

- After gaps are fixed, run **`streamclip-technical-design`** to refresh `docs/TECHNICAL_DESIGN.md`
- Figma visuals: `docs/design/FIGMA_LINKS.md`
