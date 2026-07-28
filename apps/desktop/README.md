# qClip Desktop (Electron)

Tray app that spawns the embedded Python sidecar and opens the UI in a
`BrowserWindow` at `http://127.0.0.1:8765/`.

**No Docker required** for desktop develop, verify, or installer builds. Docker is
only for the optional self-host / operator stack.

## Prerequisites

| | Windows | macOS |
|--|---------|-------|
| Node | 20+ | 20+ |
| Python | 3.11+ (`pip install -r requirements.txt` or `requirements-desktop.txt`) | same |
| ffmpeg | `.\scripts\download_ffmpeg_windows.ps1` → `bin/ffmpeg/` | `./scripts/download_ffmpeg_macos.sh` → `bin/ffmpeg/` |
| Extra | — | Apple Silicon + Xcode CLT for DMG builds |

Repo root on `PATH` is not required — the app uses `REPO_ROOT` for the dev sidecar cwd.

## Development (Windows, no Docker)

```powershell
# One-time: ffmpeg into bin\ffmpeg\
.\scripts\download_ffmpeg_windows.ps1

# Terminal 1 — optional: run sidecar alone for debugging
.\scripts\run_desktop_sidecar.ps1

# Terminal 2 — Electron shell (spawns sidecar automatically in dev)
cd apps\desktop
npm install
npm run start
```

`npm run start:sidecar-dev` only launches the Python sidecar (same env as Electron dev).

## Development (macOS, no Docker)

```bash
./scripts/download_ffmpeg_macos.sh

# Optional sidecar alone
python -m desktop_sidecar

cd apps/desktop
npm install
npm run start
```

Environment (set automatically in Electron dev):

| Variable | Default |
|----------|---------|
| `STREAMCLIP_CONFIG` | `config/desktop.yaml` |
| `STREAMCLIP_QUEUE__BACKEND` | `inprocess` |
| `STREAMCLIP_SIDECAR_HOST` | `127.0.0.1` |
| `STREAMCLIP_SIDECAR_PORT` | `8765` |

## Verify (desktop-only, no Docker)

From repo root:

```powershell
.\scripts\verify_desktop.ps1
```

Host Python + pytest only. Optional Docker API check (`verify_inprocess.ps1`) is **not** run.

## Production layout

Electron-builder packages `dist/**`, `assets/**`, and the staged sidecar under
`resources/sidecar/` (see `build.extraResources` in `package.json`).

### Windows NSIS installer (no Docker)

```powershell
.\scripts\download_ffmpeg_windows.ps1        # one-time; idempotent
.\scripts\build_desktop_installer.ps1
```

Produces `apps/desktop/release/qClip-Setup-win-x64.exe` and `latest.yml` (required for
`electron-updater`). The build fails if either artifact is missing.

Or stage an existing PyInstaller output only:

```powershell
.\scripts\stage_sidecar_for_electron.ps1   # asserts staged bin\ffmpeg\{ffmpeg,ffprobe}.exe
cd apps\desktop
npm run dist   # electron-builder --publish never
```

### macOS DMG (no Docker)

Build on an Apple Silicon Mac host:

```bash
./scripts/download_ffmpeg_macos.sh
./scripts/build_desktop_installer_macos.sh
```

Produces `apps/desktop/release/qClip-mac-arm64.dmg`. Full signing, notarization, and
troubleshooting: **[packaging/installer/MACOS.md](../../packaging/installer/MACOS.md)**.

## IPC (preload)

The renderer exposes `window.streamclip`:

- `version()` — app version string
- `sidecar.start()` — spawn the sidecar if not running
- `sidecar.stop()` — kill the sidecar child process
- `sidecar.health()` — `{ healthy, url }` via `/api/health`

## Auto-update

`electron-updater` checks GitHub Releases on startup when packaged (disable with
`STREAMCLIP_AUTO_UPDATE=0`). Tray menu **Check for updates** triggers a manual check.
Configure `build.publish` and sign builds before shipping — see
`packaging/installer/README.md`.

## CI / GitHub Actions

The `desktop-release.yml` workflow handles the full build and release pipeline:

1. Downloads ffmpeg via `scripts/download_ffmpeg_windows.ps1`
2. Installs Python ML deps (`requirements-desktop.txt`)
3. Installs Node deps for `web/` and `apps/desktop/`
4. Runs `scripts/build_desktop_installer.ps1` (UI export → PyInstaller → electron-builder NSIS)
5. Uploads `qClip-Setup-win-x64.exe` + `latest.yml` via `softprops/action-gh-release`

`npm run dist` uses `--publish never` so electron-builder never tries to push to GitHub
independently. All GitHub Release uploads go through the dedicated workflow step using
`GITHUB_TOKEN`.
