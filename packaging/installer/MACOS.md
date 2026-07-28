# macOS desktop installer (§5) — builders

**End users:** install the **`.dmg`** — see [docs/BETA_DOWNLOAD.md](../../docs/BETA_DOWNLOAD.md)
(macOS one-click). Unsigned betas: **right-click → Open**. Docker is optional for
self-host / operators, not required for the desktop product.

qClip on macOS follows the same **Electron shell + PyInstaller sidecar** layout as
Windows ([ADR-001](../../docs/ADR-001-desktop-packaging.md)). This document covers the
DMG **build** path; Windows NSIS remains in [README.md](./README.md).

**Status:** build scripts + CI job are ready. Produce a real `.dmg` on a **Mac host**
(Apple Silicon). Running `scripts/build_desktop_installer_macos.sh` on Linux/Windows
exits early with a clear error.

## Architecture decision (§5.5)

| Choice | Decision |
|--------|----------|
| First ship | **arm64** (Apple Silicon) only → `qClip-mac-arm64.dmg` |
| Later | x86_64 and/or **universal2** if Intel Mac demand appears |
| Rationale | MPS / CTranslate2 arm64 wheels; smaller artifact; matches current creator hardware |

`apps/desktop/package.json` `build.mac` + `build.dmg` both use
`artifactName: qClip-mac-{arch}.${ext}` with `arch: ["arm64"]`.

## Data directory (§5.4)

Frozen sidecar uses:

`~/Library/Application Support/qClip`

(override with `STREAMCLIP_DESKTOP_DATA_DIR`). See `packaging/README.md`.

## Build (Mac host)

Requires: macOS Apple Silicon, Node 20+, Python 3.11+, Xcode CLT, ~15 GB free disk.

```bash
cd /path/to/streamclip
chmod +x scripts/build_desktop_installer_macos.sh
./scripts/build_desktop_installer_macos.sh
```

The script **fails closed** if any of these are missing after their steps:

- `bin/ffmpeg/ffmpeg` + `ffprobe` (auto-downloads arm64 via `download_ffmpeg_macos.sh`)
- `static/ui/index.html` + `static/ui/_next`
- `dist/streamclip-sidecar/streamclip-sidecar` (no `.exe`)
- `apps/desktop/release/qClip-mac-arm64.dmg`

Reuse existing artifacts:

```bash
./scripts/build_desktop_installer_macos.sh --skip-ui --skip-sidecar
```

Expected output:

`apps/desktop/release/qClip-mac-arm64.dmg`

Post-build verify (also runs at end of build):

```bash
./scripts/verify_desktop_installer_macos.sh apps/desktop/release/qClip-mac-arm64.dmg
```

Static UI: `scripts/build_desktop_ui.sh` (no PowerShell required).

### ffmpeg (§5.1)

`scripts/download_ffmpeg_macos.sh` pulls **arm64** static builds from
[ffmpeg.martin-riedl.de](https://ffmpeg.martin-riedl.de/) (VideoToolbox-capable).
It **refuses** Intel-only binaries (evermeet.cx is not used — Intel only).

Runtime encode selection: `core/gpu_profile.py` prefers `h264_videotoolbox` on Darwin,
then `libx264`.

### Sidecar binary name

PyInstaller on Darwin produces `dist/streamclip-sidecar/streamclip-sidecar` (**no** `.exe`).
The macOS build script stages that tree into `apps/desktop/.staging/sidecar/` and refuses
a Windows `.exe` copy.

### §5.2 MPS / CTranslate2 arm64

| Piece | Status |
|-------|--------|
| Device probes / auto→MPS | ✅ `core/gpu_profile.py` |
| `requirements-desktop.txt` CPU-safe defaults | ✅ keep; Apple wheels on Mac builder |
| Live Torch MPS + CTranslate2 arm64 in sidecar | Needs Mac host / CI green build |
| DMG artifact | Script + CI; upload as workflow artifact even when unsigned |

## Code signing & notarization (Gatekeeper)

Unsigned local DMGs are supported and are a valid beta path. Without a Developer ID
identity the build script sets:

```bash
export CSC_IDENTITY_AUTO_DISCOVERY=false
```

Users open unsigned apps via **right-click → Open** the first time.

### Optional env vars (do not invent credentials)

| Variable | Purpose |
|----------|---------|
| `CSC_LINK` | Path to `.p12` / certificate file (or use keychain) |
| `CSC_KEY_PASSWORD` | Certificate password when using `CSC_LINK` |
| `CSC_NAME` | Keychain identity name (alternative to `CSC_LINK`) |
| `APPLE_ID` | Apple ID for notarization |
| `APPLE_APP_SPECIFIC_PASSWORD` | App-specific password |
| `APPLE_TEAM_ID` | Team ID |
| `APPLE_API_KEY` / `APPLE_API_KEY_ID` / `APPLE_API_ISSUER` | App Store Connect API key auth (alt) |

When these are unset, the script **fails soft** (unsigned DMG + skip notarize).
When set, electron-builder codesigns with Hardened Runtime; `scripts/notarize_macos_artifact.sh`
submits + staples the DMG.

```bash
./scripts/notarize_macos_artifact.sh apps/desktop/release/qClip-mac-arm64.dmg
```

Entitlements: `apps/desktop/assets/entitlements.mac.plist` (JIT / dyld / disable library
validation for Electron + PyInstaller + ffmpeg spawn; network client/server for local API).

## Install layout (target)

```
qClip.app/
  Contents/
    MacOS/qClip
    Resources/
      sidecar/
        streamclip-sidecar
        _internal/
```

User data: `~/Library/Application Support/qClip/` (§5.4).

## CI

`.github/workflows/desktop-release.yml` → `macos-installer` on `macos-latest`:

1. Downloads arm64 ffmpeg
2. Builds UI + sidecar + DMG (`STREAMCLIP_ALLOW_NON_ARM64=1` if runner arch ≠ arm64)
3. Sets `CSC_IDENTITY_AUTO_DISCOVERY=false` when Apple signing secrets are absent
4. Uploads `qClip-mac-arm64.dmg` as a workflow artifact (`if-no-files-found: warn`)
5. Attaches DMG to the GitHub Release on tag pushes (`fail_on_unmatched_files: false`)
6. Job `continue-on-error: true` so Windows release is never blocked

## Related

- End-user install: `docs/BETA_DOWNLOAD.md`
- Builder notes: `docs/MACOS_INSTALLER.md`
- Windows installer: `packaging/installer/README.md`
- Build script: `scripts/build_desktop_installer_macos.sh`
- Electron config: `apps/desktop/package.json` → `build.mac` / `build.dmg`
