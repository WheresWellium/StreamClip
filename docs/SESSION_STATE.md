# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-08-03 (matrix GREEN + verify_desktop_release GREEN)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `master` | next: clean-VM (O4d) / EV (O11) | — | beta.24; matrix 180/180; pre-ship gate green |

## Pipeline capability (desktop)

```
create → ingest → transcribe → highlights → virality → fan-out → process_clip×N → finalise
```

| Layer | Reality |
|-------|---------|
| Discovery scores | Audio / novelty / motion / chat (real) |
| Virality | LLM when Ollama up; else **heuristic** 0–100 (`virality_source`) |
| Create matrix | **180/180 green** — `tmp/matrix-pipeline-timing/summary.json` |
| Support (F13) | Packaged → henna → GitHub Issues + Project #4 |

## Shipped

- **1.0.0-beta.24** Latest — Win Setup + Mac arm64 DMG
- U78 create→live overview + U79 clip-count submit
- Matrix harness: `scripts/matrix_create_pipeline_timing.py` (+ SDK launcher)

## Still operator-gated

Clean-VM install→first-clip ☐ · EV / notarization ☐ · universal Mac DMG ☐

## Download

Windows → https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe  
Mac (arm64) → https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-mac-arm64.dmg  
Henna → https://streamclip-henna.vercel.app/
