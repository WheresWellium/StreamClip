# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-08-03 (pre-redeploy polish)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `master` | pre-redeploy polish | — | henna F13 honesty; installer rebuild optional |

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
| Support (F13) | Packaged → henna → GitHub Issues + [Project #4](https://github.com/users/WheresWellium/projects/4) |

## Pre-redeploy checklist

| Check | Status |
|-------|--------|
| Latest = v1.0.0-beta.22 Win + Mac arm64 | GO |
| Henna download links beta.22 | GO |
| support-ingest → Issues + Project #4 | GO (#15/#16) |
| Henna home F13 copy (not local-only) | polish this cut |
| In-app toast / health-checklist copy | needs **installer rebuild** (beta.23) to reach testers |
| Clean-VM / EV / notarization | still operator-gated |

## Still operator-gated

Clean-VM install→first-clip ☐ · EV / notarization ☐ · universal Mac DMG ☐

## Download

Windows → https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe  
Mac (arm64) → https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-mac-arm64.dmg  
Henna → https://streamclip-henna.vercel.app/
