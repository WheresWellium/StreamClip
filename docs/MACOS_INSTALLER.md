# macOS installer — builder notes

**End users:** you do **not** need this page. Install with Docker on Mac — see [Get StreamClip](BETA_DOWNLOAD.md) (macOS tab).

**Builders / friends with a Mac:** use this when producing an unsigned `.dmg` for the future one-click path (MASTER_TODO §5).

---

## What you are building

Electron shell + PyInstaller sidecar → `apps/desktop/release/StreamClip-mac-arm64.dmg` (Apple Silicon first).

This is **not** required for beta testers to run StreamClip today.

## Prerequisites

| Need | Notes |
|------|--------|
| Mac host | Apple Silicon preferred |
| Xcode Command Line Tools | `xcode-select --install` |
| Node.js 20+ | [nodejs.org](https://nodejs.org) or Homebrew |
| Python 3.11+ | `python3 --version` |
| ~15 GB free disk | Sidecar + Electron are large |
| PowerShell Core (optional) | `brew install --cask powershell` — for `build_desktop_ui.ps1`, or pre-copy `static/ui` |

**Accounts:** none for an unsigned local DMG. No Apple Developer Program required until you want Gatekeeper-clean notarization.

## Build

```bash
cd /path/to/streamclip
chmod +x scripts/build_desktop_installer_macos.sh
./scripts/build_desktop_installer_macos.sh
```

Post-build verification (also runs automatically at end of the build script):

```bash
chmod +x scripts/verify_desktop_installer_macos.sh
./scripts/verify_desktop_installer_macos.sh apps/desktop/release/StreamClip-mac-arm64.dmg
```

Expected artifact: `apps/desktop/release/StreamClip-mac-arm64.dmg`

First open of an unsigned app: **right-click → Open**.

## Signing (optional, later)

Set only when you have a Developer ID certificate:

| Variable | Purpose |
|----------|---------|
| `CSC_LINK` / `CSC_KEY_PASSWORD` | `.p12` signing |
| `CSC_NAME` | Keychain identity instead of `CSC_LINK` |
| `APPLE_ID` / `APPLE_APP_SPECIFIC_PASSWORD` / `APPLE_TEAM_ID` | Notarization |

Unset → script builds an **unsigned** DMG (`CSC_IDENTITY_AUTO_DISCOVERY=false`).

## Known gaps (scaffold vs Mac host)

| Item | Done without Mac | Still needs Mac host |
|------|------------------|----------------------|
| §5.1 VideoToolbox encode selection | ✅ `gpu_profile` / `export_video` + tests | Bundle Darwin ffmpeg; live encode smoke |
| §5.2 MPS Whisper / YOLO | ✅ device probe + auto fallback | arm64 Torch + CTranslate2 wheels in sidecar; MPS smoke |
| §5.3 Gatekeeper | Unsigned DMG script | Developer ID sign + notarize |
| DMG build | Script + CI scaffold | Successful arm64 `.dmg` on a Mac runner |

Full matrix: `packaging/installer/MACOS.md` (§5.1 / §5.2 sections).

## Related

- [Get StreamClip (Docker — Windows & Mac)](BETA_DOWNLOAD.md)
- [Beta quickstart](BETA_TESTER_QUICKSTART.md)
- [ADR-001 Desktop packaging](ADR-001-desktop-packaging.md)
