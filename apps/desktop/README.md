# StreamClip Desktop (Electron)

Tray app that spawns the embedded Python sidecar and opens the UI in a
`BrowserWindow` at `http://127.0.0.1:8765/`.

## Prerequisites

- Node.js 20+
- Python 3.11+ with repo dependencies installed (`pip install -r requirements.txt`)
- Repo root on `PATH` is not required — the app uses `REPO_ROOT` for dev sidecar cwd
- **ffmpeg + ffprobe** in `bin/ffmpeg/` (not committed — download once before building):
  ```powershell
  .\scripts\download_ffmpeg_windows.ps1
  ```

## Development

```powershell
# Terminal 1 — optional: run sidecar alone for debugging
cd D:\Projects\streamclip
.\scripts\run_desktop_sidecar.ps1

# Terminal 2 — Electron shell (spawns sidecar automatically in dev)
cd apps\desktop
npm install
npm run start
```

`npm run start:sidecar-dev` only launches the Python sidecar (same env as Electron dev).

Environment (set automatically in dev):

| Variable | Default |
|----------|---------|
| `STREAMCLIP_CONFIG` | `config/desktop.yaml` |
| `STREAMCLIP_QUEUE__BACKEND` | `inprocess` |
| `STREAMCLIP_SIDECAR_HOST` | `127.0.0.1` |
| `STREAMCLIP_SIDECAR_PORT` | `8765` |

## Production layout

Electron-builder packages `dist/**`, `assets/**`, and the staged sidecar under
`resources/sidecar/` (see `build.extraResources` in `package.json`).

Build the full NSIS installer from repo root (ffmpeg must be downloaded first):

```powershell
.\scripts\download_ffmpeg_windows.ps1        # one-time; idempotent
.\scripts\build_desktop_installer.ps1
```

Or stage an existing PyInstaller output only:

```powershell
.\scripts\stage_sidecar_for_electron.ps1
cd apps\desktop
npm run dist   # electron-builder --publish never (use npx electron-builder --publish always to publish manually)
```

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
5. Uploads `StreamClip-Setup-win-x64.exe` + `latest.yml` via `softprops/action-gh-release`

`npm run dist` uses `--publish never` so electron-builder never tries to push to GitHub
independently. All GitHub Release uploads go through the dedicated workflow step using
`GITHUB_TOKEN`.
