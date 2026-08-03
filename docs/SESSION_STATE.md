# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-08-03 (beta.20 feedback polish → beta.21)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `master` | feedback polish ship | — | Waves 1–4 landed |

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

## Feedback polish (this pass)

- SQLite WAL (on-disk) + busy_timeout; support commit retry; henna dedupe
- Job error boundary: Refresh + Report; clip render error banner
- Caption color + reframe pan/zoom in `render_overrides`
- OAuth wizard: Google/TikTok console links + desktop redirect URIs

## Still operator-gated

Clean-VM manual sign-off ☐ · EV cert ☐

## Download

Target → **1.0.0-beta.21** (publish in flight)  
https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe
