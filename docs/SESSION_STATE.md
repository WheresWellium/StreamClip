# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-08-03 (gap analysis rev 12)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `cursor/beta21-master-polish` | gap rev12 + polish | — | U73–U76 partial-fail recovery |

## Pipeline capability (desktop)

```
create → ingest → transcribe → highlights → virality → fan-out → process_clip×N → finalise
```

| Layer | Reality |
|-------|---------|
| Discovery scores | Audio / novelty / motion / chat (real) |
| Virality | LLM when Ollama up; else **heuristic** 0–100 (`virality_source`) |
| Edit without re-render | Title / hook / approval only |
| Edit + re-render | Trim, captions, colors, reframe preset/pan/zoom, overlays, aspect |
| Support (F13) | Packaged → henna `support-ingest` + SMTP (not n8n) |

## Feedback polish (landed)

- SQLite WAL + busy_timeout; support commit retry (no rollback-on-lock)
- ERROR clips: Edit / Regenerate + Save re-queue
- Re-render toast keys off clip.status (not stale job done)
- Editor: dirty hint, CSS pan/zoom preview, color reset, Escape confirm
- Heuristic face badge + factor reason; OAuth Copy URI; error prefill
- Gap rev12: partial-fail SSE honesty + job `error` still editable

## Still operator-gated

Clean-VM manual sign-off ☐ · EV cert ☐ · publish beta.22 when ready

## Download

Latest → **1.0.0-beta.21**  
https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe
