# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-08-03 (stale-folder audit)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `cursor/stale-folder-audit-31fb` | Stale folder review post beta.23/24 | stale-folder-audit | `docs/STALE_FOLDER_AUDIT.md`, version drift docs, sidecar `assets/` datas |
| `master` | — | — | beta.24 Latest; ping friend to upgrade |

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

## Shipped

- **1.0.0-beta.24** Latest — Win Setup + Mac arm64 DMG
- U78 create→live overview + U79 clip-count when More options collapsed
- F13 → GitHub Issues + Project #4

## Still operator-gated

Clean-VM install→first-clip ☐ · EV / notarization ☐ · universal Mac DMG ☐

## Audit note (2026-08-03)

No stale top-level folder is deletable. Debt = doc/version drift + OpenAPI regen + PLAN/MASTER phase rename. Sidecar now bundles root `assets/` when `manifest.json` present. Full write-up: `docs/STALE_FOLDER_AUDIT.md`.

## Download

Windows → https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe  
Mac (arm64) → https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-mac-arm64.dmg  
Henna → https://streamclip-henna.vercel.app/
