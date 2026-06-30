---
name: streamclip-technical-design
description: >-
  Authors and maintains StreamClip technical design documents (TDD) from the
  actual codebase — architecture, data flows, module boundaries, config, and
  deployment. Use when creating or updating technical design docs, architecture
  documentation, system design, ADRs, or before major refactors.
---

# StreamClip Technical Design Document

## When to run

- New subsystem (ingest, auth, export pipeline)
- Post gap-analysis remediation
- User asks for TDD, architecture doc, or system design
- Onboarding senior engineers

## Primary output

**`docs/TECHNICAL_DESIGN.md`** — single source of truth. Update sections in place; bump **Revision** at top.

Optional: FigJam diagrams via Figma MCP (see [diagrams.md](diagrams.md)).

## Workflow

```
TDD progress:
- [ ] Read current docs/GAP_ANALYSIS.md (if exists)
- [ ] Map runtime topology (docker-compose, services)
- [ ] Document pipeline task chain
- [ ] Document data model + storage keys
- [ ] Document config surface
- [ ] Document API + web contract
- [ ] Document deployment + observability
- [ ] List known limitations (honest)
- [ ] Refresh Figma links section
```

## Document template

Write `docs/TECHNICAL_DESIGN.md` using this structure:

```markdown
# StreamClip — Technical Design

**Revision:** N (YYYY-MM-DD)
**Status:** Draft | Active | Superseded

## 1. Purpose & scope
What StreamClip does; in/out of scope.

## 2. Goals & non-goals
| Goal | Non-goal |
|------|----------|

## 3. Runtime architecture
Mermaid or ASCII: Browser → Next.js → FastAPI → Celery → Redis/Postgres/MinIO/Ollama.

### 3.1 Services (docker-compose)
Table: service, port, responsibility.

### 3.2 Request paths
- Create job (URL vs upload)
- Presigned upload/download (browser ↔ MinIO direct)

## 4. Pipeline design

### 4.1 Task chain
`start_pipeline` → `run_ingest` → `run_transcribe` → `run_highlights` → `fan_out_clips` → `process_clip` × N → `finalise_job`

Per task: inputs, outputs, storage keys, failure behavior.

### 4.2 Ingest model
`IngestService`, processing tiers, canonical `source.mp4`, `pipeline_hints` in `config_snapshot`.

### 4.3 Highlight detection
Signals, guaranteed clips fallback, NMS, boundary snap.

### 4.4 Clip processing
Extract → reframe → caption → overlay → upload. Export config (`codec`, `fps`, `crf`).

## 5. Data model
- Postgres: Job, Clip, User (if used)
- MinIO key layout: `jobs/{id}/source/`, `transcript/`, clip outputs
- Redis: Celery broker, progress pub/sub, rate limits

## 6. Configuration
`config.yaml` + `STREAMCLIP_*` env vars. Sub-configs: whisper, llm, highlight, reframe, export, ingest, storage, auth.

## 7. API & web contract
Key endpoints; Server Actions; SSE progress schema (`ProgressEvent`).

## 8. Security & auth
JWT (when enabled), anonymous dev mode, owner scoping, rate limits.

## 9. Observability
`/metrics`, Flower, structured logs (`log_json`).

## 10. Deployment
Reference `deploy/PRODUCTION.md`; CPU vs GPU profiles.

## 11. Known limitations
Pulled from GAP_ANALYSIS intentional deferrals — no marketing language.

## 12. Appendix
- Reframe preset table (actual `PRESETS` values)
- Caption styles
- Figma diagram links
```

## Authoring rules

1. **Ground in code** — every architectural claim needs a file path
2. **Honest limitations** — if NVENC requires GPU worker + codec wiring, say so
3. **No duplicate README marketing** — TDD is implementer-focused
4. **Keep Mermaid valid** — no emojis; quote edge labels
5. After writing, run gap analysis skill to catch new drift

## Figma diagrams

See [diagrams.md](diagrams.md) for:
- Pipeline flowchart (Celery stages)
- System architecture
- UX journey (create → progress → clips)
- Module mindmap (hub stickies in FigJam)

## Related files

| File | Role |
|------|------|
| `docs/GAP_ANALYSIS.md` | Open gaps |
| `docs/design/FIGMA_LINKS.md` | Diagram URLs |
| `README.md` | User-facing overview (keep in sync for major features) |
