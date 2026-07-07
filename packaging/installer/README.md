# Windows desktop installer (§4.10)

StreamClip ships as an **NSIS installer** produced by [electron-builder](https://www.electron.build/)
from `apps/desktop`. The installer bundles:

1. **Electron shell** — tray app + `BrowserWindow` UI
2. **PyInstaller sidecar** — full ML stack (~1.1 GB) under `resources/sidecar/`
3. **Static web UI** — served by the sidecar at `http://127.0.0.1:8765/`

## Build

From repo root (requires Node 20+, Python 3.11+, ~15 GB free disk):

```powershell
cd C:\Users\locat\Projects\streamclip
.\scripts\build_desktop_installer.ps1
```

Output: `apps/desktop/release/StreamClip Setup <version>.exe`

Reuse existing sidecar/UI artifacts:

```powershell
.\scripts\build_desktop_installer.ps1 -SkipUi -SkipSidecar
```

## Code signing (production)

Unsigned builds trigger **Windows SmartScreen** (“Windows protected your PC”).
Beta testers can click **More info → Run anyway** (`docs/BETA_KNOWN_ISSUES.md`).

Local dev builds without a certificate should set:

```powershell
$env:CSC_IDENTITY_AUTO_DISCOVERY = "false"
```

(`build_desktop_installer.ps1` sets this automatically when `CSC_LINK` is unset — avoids
electron-builder winCodeSign symlink errors on Windows without Developer Mode.)

For production, purchase an **EV code-signing certificate** (recommended for immediate
SmartScreen reputation) or a standard Authenticode cert from a Microsoft-trusted CA.

`package.json` sets `win.signAndEditExecutable: false` so unsigned local builds work
on Windows without Developer Mode (avoids electron-builder winCodeSign symlink errors).
For signed production releases, set it to `true` when `CSC_LINK` is configured.

Set before `build_desktop_installer.ps1`:

| Variable | Purpose |
|----------|---------|
| `CSC_LINK` | Path to `.pfx` certificate file |
| `CSC_KEY_PASSWORD` | PFX password |

electron-builder signs the Electron app, NSIS installer, and bundled binaries when these
are set. Optional manual re-sign of the sidecar exe alone:

```powershell
$env:SIGNTOOL = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe"
.\scripts\sign_windows_artifact.ps1 -Path dist\streamclip-sidecar\streamclip-sidecar.exe
```

Timestamp server defaults to DigiCert; override with `SIGN_TIMESTAMP_URL`.

## Auto-update

`electron-updater` is configured for **GitHub Releases** (`apps/desktop/package.json`
`build.publish`). To enable in production:

1. Sign builds (updates rejected on Windows if unsigned).
2. Create a GitHub release tagged `v<version>` matching `apps/desktop/package.json` `version`.
3. Upload the NSIS `latest.yml` + Setup exe produced by electron-builder.
4. Set `GH_TOKEN` when running `npm run dist` for publish, or upload manually.

Users check via tray menu **Check for updates** (calls `autoUpdater.checkForUpdatesAndNotify()`).

Disable auto-update checks: `STREAMCLIP_AUTO_UPDATE=0`.

## MSIX (future)

NSIS is the current target (electron-builder default, supports large `extraResources`).
MSIX remains an option for Microsoft Store distribution but adds complexity for the
1 GB sidecar and GPU/ML native DLLs. Track separately if Store listing is required.

## Install layout

```
C:\Program Files\StreamClip\
  StreamClip.exe
  resources\
    sidecar\
      streamclip-sidecar.exe
      _internal\   (PyInstaller bundle)
```

User data (SQLite, models, workspace): `%LOCALAPPDATA%\StreamClip\` (§4.18).
