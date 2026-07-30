# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-30 (Windows beta.6 republished with in-app Help)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `master` | Phase 0 monitor | — | Win distribute ready |

## Readiness

| Metric | % | Notes |
|--------|---|-------|
| Tester-ready **shipped** | **~90%** | Win `.exe` live w/ Help UI; Mac arm64 interim |
| Phase 0 **exit** | **~70%** | O4/O5/O11; Mac universal ☐; notarize/EV ☐ |

## Shipped

| Item | Status |
|------|--------|
| Win `qClip-Setup-win-x64.exe` | ✅ republished 2026-07-30 (~393 MB, includes `/help`) |
| Mac `qClip-mac-arm64.dmg` | ✅ on release (Silicon-only) |
| Mac universal pipeline | ✅ scripts ready — ☐ host rebuild |

## Blockers (human-only)

- O4 cohort exit · O5 on-call · O11 EV signing
- Mac universal upload · notarization

## Next steps

1. Push henna docs if not already on origin.
2. Mac: rebuild universal DMG when ready.
3. Fill O4 / O5.
