# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-28

## Active chats

| Chat | Branch | Focus |
|------|--------|-------|
| cloud-desktop-first | `cursor/desktop-first-completion-39d9` | Desktop solo gate — human smoke remaining |

## Current focus

Henna docs polished — **Desktop install guide** is primary nav. Live after merge to `master` (Vercel rebuild).

## Henna (published nav)

- Install → DESKTOP_SOLO_USER_GUIDE, BETA_DOWNLOAD, BETA_TESTER_QUICKSTART
- Using qClip → tutorials
- Help → Troubleshooting, Known issues
- Operator pages excluded from henna build

## Agent-complete

- A1–A2: Win exe fetched; SHA256 in `apps/desktop/release/SHA256SUMS.txt`
- C1–C2: `dist/qclip-beta-kit-DesktopSolo-*.zip` with installer
- Scripts: `run_windows_solo_smoke.ps1`, `run_macos_solo_smoke.sh`, `finish_desktop_solo_release.sh`, `build_macos_solo.sh`, `package_desktop_solo_kit.sh`
- Docs: DESKTOP_SIGNING, RELEASE_NOTES_beta.6; BETA_TESTER_QUICKSTART + TUTORIAL_INSTALL desktop-first
- Henna solo gate live

## Human remaining

1. Windows: `.\scripts\run_windows_solo_smoke.ps1` → PASS in gate A
2. Mac: `./scripts/build_macos_solo.sh` + `./scripts/run_macos_solo_smoke.sh`
3. Upload kit; `CONFIRM_SOLO_SMOKE=1 ./scripts/finish_desktop_solo_release.sh 1.0.0-beta.6`
4. Merge PR #7; tag `v1.0.0-beta.6`

## Key paths

- Gate: `docs/DESKTOP_SOLO_GATE.md`
- Kit: `dist/qclip-beta-kit-DesktopSolo-*.zip`
- Win smoke: `scripts/run_windows_solo_smoke.ps1`
- Mac: `scripts/build_macos_solo.sh` + `run_macos_solo_smoke.sh`
