# Desktop release checklist (§4.10 Windows + §5 macOS)

Use before tagging `v*` for GitHub Releases.

## Windows `.exe`

1. `.\scripts\download_ffmpeg_windows.ps1` (idempotent)
2. `.\scripts\verify_desktop.ps1` — db, storage, ffmpeg smoke
3. `.\scripts\build_desktop_installer.ps1` — produces `StreamClip-Setup-win-x64.exe`
4. **EV code signing** — `.\scripts\sign_windows_artifact.ps1` (see `packaging/installer/README.md`)
5. Upload to GitHub Release + bump `docs/BETA_DOWNLOAD.md` version

## macOS `.dmg` (Mac host)

1. `./scripts/build_desktop_installer_macos.sh`
2. `./scripts/verify_desktop_installer_macos.sh apps/desktop/release/StreamClip-mac-arm64.dmg`
3. Optional: Developer ID sign + notarize (`packaging/installer/MACOS.md`)
4. Bump `docs/BETA_DOWNLOAD.md` macOS row

## CI

- `.github/workflows/desktop-release.yml` — Windows job (required), macOS job (scaffold, `continue-on-error: true` until §5.1–5.2 land)

## Beta kit

```powershell
.\scripts\prepare_beta_kit.ps1 -Mode Source   # default runnable tree
.\scripts\prepare_beta_kit.ps1 -Mode ProdImages
```

Testers run `.\scripts\start_local.ps1` then `.\scripts\verify_stack.ps1`.
