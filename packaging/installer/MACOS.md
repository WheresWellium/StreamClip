# macOS desktop installer (§5) — builders

**Beta testers / end users:** install with **Docker on Mac**, not this DMG path —
see [docs/BETA_DOWNLOAD.md](../../docs/BETA_DOWNLOAD.md) (macOS tab) and
[docs/MACOS_INSTALLER.md](../../docs/MACOS_INSTALLER.md).

StreamClip on macOS follows the same **Electron shell + PyInstaller sidecar** layout as
Windows ([ADR-001](../../docs/ADR-001-desktop-packaging.md)). This document covers the
DMG **build** path; Windows NSIS remains in [README.md](./README.md).

**Status:** scaffold ready. A real `.dmg` must be built on a **Mac host** (Apple Silicon
preferred). Running `scripts/build_desktop_installer_macos.sh` on Windows exits early.

## Architecture decision (§5.5)

| Choice | Decision |
|--------|----------|
| First ship | **arm64** (Apple Silicon) only |
| Later | x86_64 and/or **universal2** if Intel Mac demand appears |
| Rationale | MPS / CTranslate2 arm64 wheels; smaller artifact; matches current creator hardware |

`apps/desktop/package.json` `build.mac` targets `dmg` + `arch: ["arm64"]` with
`artifactName: StreamClip-mac-{arch}.${ext}`.

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

`apps/desktop/release/StreamClip-mac-arm64.dmg`

Static UI today is built via `scripts/build_desktop_ui.ps1` — on Mac install
[PowerShell Core](https://github.com/PowerShell/PowerShell) (`pwsh`) or pre-copy
`static/ui` from a Windows/CI build.

### Sidecar binary name

PyInstaller on Darwin produces `dist/streamclip-sidecar/streamclip-sidecar` (**no** `.exe`).
The macOS build script stages that tree into `apps/desktop/.staging/sidecar/` and refuses
a Windows `.exe` copy.

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

**Operator note:** pin arm64 wheels on the Mac builder (`pip install torch` from the
official macOS arm64 index; CTranslate2 must publish `macosx_arm64` for the Python
version in use). Intel Mac / universal2 is deferred (§5.5). Until the Mac build lands,
beta testers use **Docker on Mac** (`docs/BETA_DOWNLOAD.md`).

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
codesigns with Hardened Runtime (`build/entitlements.mac.plist`) and can notarize if
Apple ID env is present.

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

Windows release job (`.github/workflows/desktop-release.yml`) stays unchanged. A future
`macos-latest` job should call `build_desktop_installer_macos.sh` without breaking the
Windows NSIS path.

## Related

- Windows installer: `packaging/installer/README.md`
- Packaging map: `packaging/README.md`
- Build script: `scripts/build_desktop_installer_macos.sh`
- Electron config: `apps/desktop/package.json` → `build.mac`
