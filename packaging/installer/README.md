# Windows desktop installer (§4.10)

> **macOS DMG:** see [MACOS.md](./MACOS.md) (`scripts/build_desktop_installer_macos.sh`, Mac host required).

qClip ships as an **NSIS installer** produced by [electron-builder](https://www.electron.build/)
from `apps/desktop`. The installer bundles:

1. **Electron shell** — tray app + `BrowserWindow` UI
2. **PyInstaller sidecar** — full ML stack (~1.1 GB) under `resources/sidecar/`
3. **Static web UI** — served by the sidecar at `http://127.0.0.1:8765/`

## Build

From repo root (requires Node 20+, Python 3.11+, ~15 GB free disk):

```powershell
cd D:\Projects\streamclip
.\scripts\build_desktop_installer.ps1
```

Output: `apps/desktop/release/qClip-Setup-win-x64.exe`

Stable public download URL (after GitHub Release):

`https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe`

Docs landing page: `docs/BETA_DOWNLOAD.md` → https://streamclip-henna.vercel.app/BETA_DOWNLOAD/

Reuse existing sidecar/UI artifacts:

```powershell
.\scripts\build_desktop_installer.ps1 -SkipUi -SkipSidecar
```

## Code signing — operator checklist (§4.10)

Unsigned builds trigger **Windows SmartScreen** (“Windows protected your PC”).
Beta testers can click **More info → Run anyway** (`docs/BETA_KNOWN_ISSUES.md`).
**Do not invent or commit certificates** — purchase from a Microsoft-trusted CA when ready.

### Local unsigned (default)

```powershell
$env:CSC_IDENTITY_AUTO_DISCOVERY = "false"
```

(`build_desktop_installer.ps1` sets this automatically when `CSC_LINK` is unset — avoids
electron-builder winCodeSign symlink errors on Windows without Developer Mode.)

`apps/desktop/package.json` sets `win.signAndEditExecutable: false` so unsigned local
builds work without Developer Mode. For signed production releases, set it to `true`
when `CSC_LINK` is configured.

### Env vars (required for signing)

| Variable | Purpose |
|----------|---------|
| `CSC_LINK` | Path to `.pfx` (local) **or** base64-encoded PFX (CI secret) |
| `CSC_KEY_PASSWORD` | PFX password |
| `SIGNTOOL` | Optional path to `signtool.exe` (auto-discovered from Windows SDK) |
| `SIGN_TIMESTAMP_URL` | Optional; default `http://timestamp.digicert.com` |

Purchase an **EV code-signing certificate** (recommended for immediate SmartScreen
reputation) or a standard Authenticode cert. Export as `.pfx` with a strong password.
Never commit the PFX or password to the repo.

### Sign locally

```powershell
# electron-builder signs app + NSIS when CSC_* are set:
$env:CSC_LINK = "C:\secure\streamclip-ev.pfx"
$env:CSC_KEY_PASSWORD = "<pfx-password>"
.\scripts\build_desktop_installer.ps1

# Optional manual re-sign of a single PE (sidecar, Setup exe, etc.):
.\scripts\sign_windows_artifact.ps1 -Path apps\desktop\release\qClip-Setup-win-x64.exe
```

### Verify signature

```powershell
# After Windows SDK install (signtool on PATH or set SIGNTOOL):
signtool verify /pa /v apps\desktop\release\qClip-Setup-win-x64.exe
```

Expect: successful Authenticode chain, publisher matching your cert subject, and a
valid timestamp. `/pa` uses the default Authenticode verification policy.

### SmartScreen notes

- **Unsigned:** SmartScreen warning is expected; document “More info → Run anyway” for beta.
- **Standard OV cert:** reputation builds over time with download volume; early installs may still warn.
- **EV cert:** typically establishes reputation faster (hardware token / cloud HSM depending on CA).
- Signing alone does not remove SmartScreen forever — keep the same publisher identity across releases.

### CI secrets (GitHub Actions)

`.github/workflows/desktop-release.yml` builds **unsigned** unless both secrets exist:

| GitHub Actions secret | Maps to |
|-----------------------|---------|
| `WINDOWS_CSC_LINK` | `CSC_LINK` (base64 of the `.pfx` file, or a path if you stage the file in the job) |
| `WINDOWS_CSC_KEY_PASSWORD` | `CSC_KEY_PASSWORD` |

When both are set, the workflow exports them and **omits**
`CSC_IDENTITY_AUTO_DISCOVERY=false` so electron-builder signs. When either is missing,
the job stays unsigned (current beta path). No placeholder certs in the repo.

Encode a PFX for the secret (operator machine, not committed):

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\secure\streamclip-ev.pfx")) |
  Set-Clipboard
```

Paste into repo **Settings → Secrets and variables → Actions → `WINDOWS_CSC_LINK`**.

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
C:\Program Files\qClip\
  qClip.exe
  resources\
    sidecar\
      streamclip-sidecar.exe
      _internal\   (PyInstaller bundle)
```

User data (SQLite, models, workspace): `%LOCALAPPDATA%\qClip\` (§4.18).

## macOS

End-user beta install is **Docker on Mac** — [docs/BETA_DOWNLOAD.md](../../docs/BETA_DOWNLOAD.md).
DMG builder notes: [MACOS.md](./MACOS.md) · [docs/MACOS_INSTALLER.md](../../docs/MACOS_INSTALLER.md).
