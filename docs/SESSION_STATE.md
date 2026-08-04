# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-08-04 (cutting 1.0.0-beta.27)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `master` | publish beta.27 | — | Twitch/upload honesty merged; Win build + Mac dispatch |

## Shipped (in flight)

- Merge: Twitch/upload honesty + React #185 + desktop Client-ID
- Version bump: `apps/desktop/package.json` → **1.0.0-beta.27**

## Next after publish

1. Confirm Latest assets Win + Mac on GitHub Releases
2. Clean-VM install→first-clip on beta.27
3. Point testers at new build (Twitch VOD + upload)

## Pipeline capability (desktop)

```
create → ingest → transcribe → highlights → virality → fan-out → process_clip×N → finalise
```

## Download

Windows → https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe  
Mac (arm64) → https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-mac-arm64.dmg  
Henna → https://streamclip-henna.vercel.app/
