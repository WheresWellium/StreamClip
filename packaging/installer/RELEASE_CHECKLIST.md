# Desktop release checklist (§4.10 Windows + §5 macOS)

Use before tagging `v*` for GitHub Releases.

## Windows `.exe`

1. `.\scripts\download_ffmpeg_windows.ps1` (idempotent; also auto-run by installer build)
2. `.\scripts\verify_desktop.ps1` — db, storage, ffmpeg smoke
3. `.\scripts\build_desktop_installer.ps1` — produces `qClip-Setup-win-x64.exe` + `latest.yml`
4. Confirm `apps/desktop/release/latest.yml` exists (electron-updater)
5. **EV code signing** (optional for unsigned beta) — `.\scripts\sign_windows_artifact.ps1` (see `packaging/installer/README.md`)
6. Publish: `.\scripts\publish_desktop_release.ps1 -Version 1.0.0-beta.N` (uploads Setup + `latest.yml`, bumps `docs/BETA_DOWNLOAD.md`)

## macOS `.dmg` (Mac host / `macos-latest` CI)

1. `./scripts/download_ffmpeg_macos.sh`
2. `./scripts/build_desktop_installer_macos.sh` (builds UI via `build_desktop_ui.sh`)
3. `./scripts/verify_desktop_installer_macos.sh apps/desktop/release/qClip-mac-arm64.dmg`
4. Optional: Developer ID sign + notarize (`packaging/installer/MACOS.md`)
5. Bump `docs/BETA_DOWNLOAD.md` macOS row when a DMG ships

## CI

- `.github/workflows/desktop-release.yml`
  - **Windows job** — required; publishes Setup exe + `latest.yml`
  - **macOS job** — scaffold on `macos-latest` with `continue-on-error: true` until §5.2–5.3 (MPS wheels + notarization) are green

## Beta kit (Docker + Windows installer)

The GitHub repo is **private** — anonymous release download URLs **404**. Do not send bare GitHub `/releases/.../download/...` links to testers.

```powershell
.\scripts\prepare_beta_kit.ps1 -Mode Source   # default runnable tree
.\scripts\prepare_beta_kit.ps1 -Mode Source -IncludeInstaller   # + installers/qClip-Setup-win-x64.exe
.\scripts\prepare_beta_kit.ps1 -Mode ProdImages
```

`-IncludeInstaller` copies from `apps/desktop/release/` or falls back to `gh release download` (collaborator auth). Attach the zip / `installers/` via invite pack, Lemon Squeezy, or Drive.

Testers run `.\scripts\start_local.ps1` then `.\scripts\verify_stack.ps1` (Docker), or run `installers\qClip-Setup-win-x64.exe` (desktop; SmartScreen → More info → Run anyway).