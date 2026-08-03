# macOS desktop installer (§5) — builders

**Beta testers / end users:** download the Apple Silicon DMG on Latest —
see [docs/BETA_DOWNLOAD.md](../../docs/BETA_DOWNLOAD.md#macos) and
[docs/MACOS_INSTALLER.md](../../docs/MACOS_INSTALLER.md).

qClip on macOS follows the same **Electron shell + PyInstaller sidecar** layout as
Windows ([ADR-001](../../docs/ADR-001-desktop-packaging.md)). This document covers the
DMG **build** path; Windows NSIS remains in [README.md](./README.md).

**Status:** Latest ships **arm64** via GHA (`STREAMCLIP_MAC_SINGLE_ARCH=arm64`).
Universal DMG still needs a Mac host + Rosetta x86 Python. Running the script on
Windows exits early.

## Architecture decision (§5.5)

| Choice | Decision |
|--------|----------|
| Ship (Latest) | Apple Silicon `qClip-mac-arm64.dmg` via CI |
| Fuller local | **universal** Electron + dual sidecars → `qClip-mac-universal.dmg` |
| Rationale | Arm64 on GHA matches Windows one-arch Latest; universal needs Rosetta |

`apps/desktop/package.json` `build.mac` defaults to `dmg` + `arch: ["universal"]` with
`artifactName: qClip-mac-${arch}.${ext}` (CI single-arch rewrites target + name).
The main process picks `sidecar/{arm64,x64}/` at runtime (`apps/desktop/src/main.ts`).

## Data directory (§5.4)

Frozen sidecar uses:

`~/Library/Application Support/StreamClip`

(override with `STREAMCLIP_DESKTOP_DATA_DIR`). See `packaging/README.md`.

## Build (Mac host)

Requires: macOS, Node 20+, Python 3.11+, Xcode CLT, ~15 GB free disk.

```bash
cd /path/to/streamclip
chmod +x scripts/build_desktop_installer_macos.sh
./scripts/build_desktop_installer_macos.sh
```

Reuse existing artifacts:

```bash
./scripts/build_desktop_installer_macos.sh --skip-ui --skip-sidecar
```

Expected output:

`apps/desktop/release/qClip-mac-universal.dmg`

**Rosetta / Intel sidecar (required for universal):** on Apple Silicon install Rosetta, then
x86_64 Homebrew Python under `/usr/local`, then re-run the script. Escape hatch:
`STREAMCLIP_MAC_SINGLE_ARCH=arm64` (Silicon-only; not for Intel testers).

Static UI is built via `scripts/build_desktop_ui.sh` (no PowerShell required).
Windows operators can still use `scripts/build_desktop_ui.ps1`.

### Sidecar binary name

PyInstaller on Darwin produces `dist/streamclip-sidecar/streamclip-sidecar` (**no** `.exe`).
The macOS build script stages **per-arch** trees into
`apps/desktop/.staging/sidecar/{arm64,x64}/` and refuses a Windows `.exe` copy.

### §5.1 VideoToolbox (code path — no Mac host required)

Runtime encode selection is wired in-repo:

- `core/gpu_profile.videotoolbox_available` probes ffmpeg for `h264_videotoolbox`
- `effective_export_codec` on Darwin: NVENC request → `h264_videotoolbox` → `libx264`
- `core/export_video.video_encode_args` emits `-q:v` for VideoToolbox
- Unit tests mock `is_darwin` (run on Windows/Linux CI)

**Still needs a Mac host:** bundling a Darwin ffmpeg binary into the DMG sidecar and a
live encode smoke on Apple Silicon. The codec fallback logic itself does not.

### §5.2 MPS / CTranslate2 arm64 — scaffold vs Mac host

| Piece | Status without Mac | Needs Mac host |
|-------|--------------------|----------------|
| `mps_available()` / `effective_whisper_device` auto→MPS | ✅ in `core/gpu_profile.py` | Live Torch MPS smoke |
| Whisper `device=mps` config path | ✅ scaffolded | Confirm faster-whisper + CTranslate2 **arm64** wheels install |
| YOLO / Torch inference on MPS | Probe only | Install `torch` macOS arm64 wheel; verify YOLO forward on MPS |
| PyInstaller sidecar with ML dylibs | Script scaffold | Build on `macos-latest` / Apple Silicon; fix dyld / entitlements |
| DMG artifact | Script + CI job (`continue-on-error`) | Successful `build_desktop_installer_macos.sh` producing `.dmg` |

**Operator note:** pin arch-matching wheels for each sidecar build (arm64 native Python +
x86_64 Python under Rosetta). CTranslate2/torch must resolve for that arch. Notarization
is still optional (§5.3).

Track remaining §5.2/§5.3 work in `docs/MASTER_TODO.md` §5.

## Code signing & notarization (Gatekeeper)

Unsigned local DMGs are supported. Without a Developer ID identity the build script sets:

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

When these are unset, the script **fails soft** (unsigned DMG). When set, electron-builder
codesigns with Hardened Runtime and can notarize if Apple ID env is present.

Entitlements live at `apps/desktop/assets/entitlements.mac.plist` (JIT / dyld needed for
Electron + native ML libs).

## Install layout (target)

```
StreamClip.app/
  Contents/
    MacOS/StreamClip
    Resources/
      sidecar/
        streamclip-sidecar
        _internal/
```

User data: `~/Library/Application Support/StreamClip/` (§5.4).

## CI note

`.github/workflows/desktop-release.yml` runs a `macos-installer` job on `macos-latest`
(arm64-capable runners). It installs `requirements-desktop.txt`, downloads Darwin ffmpeg,
builds UI via `build_desktop_ui.sh`, and produces a DMG. The job uses
`continue-on-error: true` until §5.2–5.3 are green so Windows releases are not blocked.

## Related

- Windows installer: `packaging/installer/README.md`
- Packaging map: `packaging/README.md`
- Build script: `scripts/build_desktop_installer_macos.sh`
- Electron config: `apps/desktop/package.json` → `build.mac`
