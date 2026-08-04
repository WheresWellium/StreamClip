# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-08-04 (beta.26 cut — screenrec closeout)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `master` | idle after beta.26 | — | Win+Mac on Latest; screenrec closeout shipped |

## Pipeline capability (desktop)

```
create → ingest → transcribe → highlights → virality → fan-out → process_clip×N → finalise
```

| Layer | Reality |
|-------|---------|
| Discovery scores | Audio / novelty / motion / chat (real) |
| Virality | LLM when Ollama up; else **heuristic** 0–100 (`virality_source`) |
| Create matrix | **pipeline_green 180/180** (135 short of target_clips on smoke fixture) |
| Playwright e2e | **35/35 green** + CI/verify_stack wired; live upload→clips UI deferred |
| Support (F13) | Help → henna → Project #4; health `ops_webhook_configured`; henna `project_configured` |

## Shipped

- **1.0.0-beta.26** Latest — Win Setup + Mac arm64 (screenrec M1–M7 closeout)
- U78 create→live overview + U79 clip-count submit
- Matrix harness: `scripts/matrix_create_pipeline_timing.py` (+ SDK launcher)

## Still operator-gated

Clean-VM install→first-clip ☐ · EV / notarization ☐ · universal Mac DMG ☐

## Download

Windows → https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe  
Mac (arm64) → https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-mac-arm64.dmg  
Henna → https://streamclip-henna.vercel.app/
