# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-08-03 (beta.22 distribute cut)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `master` | beta.22 ship | — | known-issues + publish |

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
| Support (F13) | Packaged → henna `support-ingest` + SMTP (`OPS_WEBHOOK_URL` only) |

## Shipped this cut (beta.22)

- Partial-fail honesty + Edit on job `error`
- Clip card respects job aspect ratio
- Dropped legacy `N8N_OPS_WEBHOOK_URL` alias
- Known-issues / gap rev 13 aligned to Latest

## Still operator-gated

Clean-VM install→first-clip ☐ · EV cert ☐

## Download

Latest → **1.0.0-beta.22**  
https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe
