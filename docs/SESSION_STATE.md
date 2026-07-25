# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-24

## Active chats

None.

## Current focus

**Desktop release:** Windows `v1.0.0-beta.4` published (Setup + `latest.yml`). Packaging/CI hardened for Win + macOS scaffold. Mac DMG still needs Apple Silicon host + Developer ID.

## Blockers

- EV Authenticode cert (§4.10) — SmartScreen warns until signed.
- macOS DMG + notarization (§5.2–5.3) — Mac host + Apple Developer.
- Phase 0 exit — T0 cohort results (§8.16).

## Validation

- Coverage ✅ 96.08%
- `verify_desktop.ps1` ✅
- Windows installer ✅ https://github.com/WheresWellium/StreamClip/releases/tag/v1.0.0-beta.4

## Next steps

1. Redeploy MkDocs so `BETA_DOWNLOAD` shows beta.4.
2. Buy EV cert; configure `WINDOWS_CSC_*` secrets.
3. Run/triage `desktop-release.yml` macOS job on Apple Silicon; notarize when Apple ID ready.
4. Optional: real app icons (`icon.ico` / `icon.icns`).

## Key paths

- Release: `scripts/publish_desktop_release.ps1`
- CI: `.github/workflows/desktop-release.yml`
- Mac: `scripts/build_desktop_installer_macos.sh`, `download_ffmpeg_macos.sh`
