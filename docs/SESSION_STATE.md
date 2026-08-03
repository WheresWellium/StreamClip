# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-08-03 (cutting beta.23)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `master` | beta.23 cut | — | Win publish + Mac GHA |

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

## Shipped this cut (beta.23)

- F13 honesty (henna + in-app checklist) + GitHub Project board
- Mac arm64 parity retained on Latest
- Toast / health-checklist copy polish in installer

## Still operator-gated

Clean-VM install→first-clip ☐ · EV / notarization ☐ · universal Mac DMG ☐

## Download

Windows → https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe  
Mac (arm64) → https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-mac-arm64.dmg  
Henna → https://streamclip-henna.vercel.app/
