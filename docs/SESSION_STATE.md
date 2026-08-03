# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-08-03 (Mac arm64 + henna prod)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `master` | — | — | Mac parity shipped; next = clean-VM / EV |

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
| Support (F13) | Packaged → henna → **GitHub Issues** (+ Project board); SMTP optional |

## Shipped

- Windows + Mac Apple Silicon on **1.0.0-beta.22** Latest
- Henna prod promoted (`streamclip-henna.vercel.app` → Latest Mac + beta.22)
- F13: in-app Help → henna → GitHub Issues + [Project #4](https://github.com/users/WheresWellium/projects/4) (verified #15/#16)
- Partial-fail honesty, heuristic virality, job-aspect cards

## Still operator-gated

Clean-VM install→first-clip ☐ · EV / notarization ☐ · universal Mac DMG ☐

## Download

Windows → https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe  
Mac (arm64) → https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-mac-arm64.dmg  
Henna → https://streamclip-henna.vercel.app/
