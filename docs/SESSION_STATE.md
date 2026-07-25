# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-24

## Active chats

None.

## Current focus

**Desktop release track** — ship Windows unsigned beta (+ harden macOS CI scaffold) for Mac/Windows testers. Coverage gate green at 96.08%. Packaging/CI gaps fixed; next: rebuild/publish Windows installer `1.0.0-beta.4`.

## Blockers

- EV Authenticode cert (§4.10) — external purchase; unsigned SmartScreen OK for wave‑1.
- macOS DMG + notarization (§5.2–5.3) — needs Mac host / green `macos-installer` CI + Apple Developer.
- Phase 0 exit still needs T0 cohort results (§8.16).

## Validation

- `scripts/verify_coverage.ps1` ✅ 96.08% (2026-07-24)
- `web` typecheck ✅
- Next: `scripts/verify_desktop.ps1` → `publish_desktop_release.ps1 -Version 1.0.0-beta.4`

## Next steps

1. Commit packaging + test fixes; push `master`.
2. Build/publish Windows installer beta.4 (Setup + `latest.yml`); bump `BETA_DOWNLOAD.md`.
3. Trigger `desktop-release.yml` macOS job (continue-on-error) and triage DMG failures on Apple Silicon.
4. Buy EV cert; Apple Developer for Gatekeeper-clean Mac.

## Key paths

- `scripts/build_desktop_installer.ps1` / `publish_desktop_release.ps1`
- `scripts/build_desktop_installer_macos.sh` / `download_ffmpeg_macos.sh` / `build_desktop_ui.sh`
- `.github/workflows/desktop-release.yml`
- `packaging/installer/{README,MACOS,RELEASE_CHECKLIST}.md`
