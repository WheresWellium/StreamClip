# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-08-04 (Twitch/upload proven; await beta.27)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `master` | Twitch/upload honesty proven (uncommitted) | — | Source-tree proof green; packaged beta.26 lacks Client-ID |

## Proof (2026-08-04)

- Source `proof_ingest_pipeline.ps1 -TwitchClipOnly`: upload done/1 + Twitch clip done/1 (`tmp/proof-ingest-pipeline-result.json`)
- Packaged `smoke_source_matrix -Source upload-video`: done/1
- Tester VOD `2836776596`: yt-dlp+Client-ID downloaded 20s video (`tmp/proof-vod-video-20s.mp4`); packaged `desktop.yaml` has **no** `twitch_client_id`
- Overlay: degrade if `sentence_transformers` missing (dev host)

## Pre-cut (verify-this 2026-08-04)

Artifacts: `tmp/verify-this/twitch-upload-honesty/verdict.md` — source proof + packaged twitch-clip + `verify_desktop_release` **green**; packaged yaml still **no** Client-ID until rebuild.

## Next

1. Merge `cursor/twitch-upload-honesty` → master
2. Rebuild UI/sidecar + publish **1.0.0-beta.27**
3. Clean-VM install→first-clip on beta.27

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
