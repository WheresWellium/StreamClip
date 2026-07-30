# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-30 (henna = download + how-to only)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `master` | Phase 0 monitor | — | Win live; Mac universal pending host rebuild |

## Readiness

| Metric | % | Notes |
|--------|---|-------|
| Tester-ready **shipped** | **~88%** | Win live; Mac arm64 on release; universal config ready |
| Phase 0 **exit** | **~70%** | O4/O5/O11; O14 notarize ☐ + universal upload ☐ |

## Shipped

| Item | Status |
|------|--------|
| beta.6 Windows installer | ✅ |
| Mac `qClip-mac-arm64.dmg` | ✅ on release (Silicon-only interim) |
| Mac **universal** pipeline | ✅ config/scripts (`--universal` + dual sidecar) — ☐ host rebuild + upload |

## Blockers (human-only)

- **Mac:** on Apple Silicon run `./scripts/build_desktop_installer_macos.sh` (needs Rosetta + `/usr/local` x86 Python), upload `qClip-mac-universal.dmg`
- O4 / O5 / O11 · notarization

## Next steps

1. Rebuild + upload `qClip-mac-universal.dmg`; remove or keep arm64 asset as fallback.
2. Deploy henna (single-page download + how-to) to Vercel.
3. Fill `BETA_COHORT_EXIT.md` (O4) / `BETA_ON_CALL.md` (O5).
