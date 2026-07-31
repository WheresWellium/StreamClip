# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-30 (Win white-screen fix republished)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `master` | Win boot fix ship | — | OUTPUT_DIR + single-instance + icons |

## Readiness

| Metric | % | Notes |
|--------|---|-------|
| Tester-ready **shipped** | **~92%** | Win white-screen root cause fixed + republished |
| Phase 0 **exit** | **~70%** | O4/O5/O11; Mac universal ☐; notarize/EV ☐ |

## Shipped

| Item | Status |
|------|--------|
| Win `qClip-Setup-win-x64.exe` | ✅ republished 2026-07-30 (~393 MB; OUTPUT_DIR under LocalAppData) |
| Mac `qClip-mac-arm64.dmg` | ✅ on release (Silicon-only) |
| Mac universal pipeline | ✅ scripts ready — ☐ host rebuild |

## Root cause (Win white screen)

Sidecar created relative `output/` under Program Files → Access denied → no :8765 → Electron blank. Multi-launch → ghost trays (no single-instance lock).

## Critical fixes in flight (branch `cursor/desktop-critical-fixes`)

- **License 500**: `licensing.license_file` default was relative (`workspace/...`) → write under Program Files → OSError → 500. Fix: sidecar sets `STREAMCLIP_LICENSING__LICENSE_FILE` under LocalAppData + `_persist_license_file` relocates on OSError.
- **Job nav loop (desktop)**: static export serves dynamic `/jobs/<id>/` from home shell. Fix: `backend/static_ui.py resolve_spa_html()` resolves exported `_` dynamic shells (`jobs/_/index.html`).
- Also on separate branch `cursor/header-back-button`: persistent header Back control.

## Blockers (human-only)

- O4 cohort exit · O5 on-call · O11 EV signing
- Mac universal upload · notarization

## Next steps

1. Commit/push crash + Electron + health-speed source if not on origin.
2. Testers: kill orphan qClip → uninstall → reinstall latest Setup.
3. Mac: rebuild universal DMG when ready.
4. Fill O4 / O5.
