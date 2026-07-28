# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-28

## Active chats

| Chat | Branch | Focus |
|------|--------|-------|
| cloud-desktop-first | `cursor/desktop-first-completion-39d9` | Desktop-only Win+mac packaging (no Docker) |

## Current focus

**Desktop distribution gate:** ship Windows `.exe` + macOS `.dmg` without Docker. Docker is operator-only.

## Blockers

- macOS DMG must be built on Apple Silicon host (CI soft-path improved; needs green artifact).
- EV Authenticode (Windows SmartScreen) + Apple notarization (Gatekeeper).
- Human smoke: [HUMAN_DESKTOP_SMOKE.md](HUMAN_DESKTOP_SMOKE.md).

## Validation

- Windows beta.5 installer published; packaging scripts fail-closed on missing exe/ffmpeg/`latest.yml`.
- macOS: arm64 ffmpeg download, unsigned CSC clear, `requirements-desktop-macos.txt`, entitlements/docs flipped to DMG-first.
- Desktop runtime: whisper medium/int8 defaults, HF cache in app-data, auto Fernet key, license status mismatch no longer wipes entitlement.
- Opsera unavailable → pip-audit/npm-audit report in `/opt/cursor/artifacts/security-scan-desktop.md`.

## Next steps

1. On Mac: `./scripts/build_desktop_installer_macos.sh` → attach `qClip-mac-arm64.dmg`.
2. `.\scripts\prepare_beta_kit.ps1 -IncludeInstaller` (Win + mac when present).
3. Human smoke both platforms; then merge PR #7.

## Key paths

- Build: `scripts/build_desktop_installer.ps1`, `scripts/build_desktop_installer_macos.sh`
- Runtime: `config/desktop.yaml`, `desktop_sidecar/run.py`, `apps/desktop/src/main.ts`
- Docs: `BETA_DOWNLOAD.md`, `RELEASE_CHECKLIST.md`, `HUMAN_DESKTOP_SMOKE.md`
