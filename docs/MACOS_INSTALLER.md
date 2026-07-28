# macOS installer — builder notes

**End users:** install **`qClip-mac-arm64.dmg`** from your invite kit / operator link —
see [Get qClip](BETA_DOWNLOAD.md). Unsigned beta: **right-click → Open**. You do **not**
need Docker for the desktop product.

**Builders:** use this page to produce the DMG on an Apple Silicon Mac (MASTER_TODO §5).

---

## What you are building

Electron shell + PyInstaller sidecar → `apps/desktop/release/qClip-mac-arm64.dmg`.

## Prerequisites

| Need | Notes |
|------|--------|
| Mac host | **Apple Silicon** (arm64) |
| Xcode Command Line Tools | `xcode-select --install` |
| Node.js 20+ | [nodejs.org](https://nodejs.org) or Homebrew |
| Python 3.11+ | `python3 --version` |
| ~15 GB free disk | Sidecar + Electron are large |

**Accounts:** none for an unsigned local DMG. Apple Developer Program only when you want
Gatekeeper-clean notarization.

## One command (operators)

On an Apple Silicon Mac, from the repo root:

```bash
./scripts/build_macos_solo.sh
```

Prints prerequisites, builds the DMG, verifies
`apps/desktop/release/qClip-mac-arm64.dmg`, then reminds you to run Finder smoke
([Desktop install guide](DESKTOP_SOLO_USER_GUIDE.md)) and copy the DMG into the invite kit.

## Build (advanced)

Same pipeline without the solo wrapper:

```bash
cd /path/to/streamclip
chmod +x scripts/build_desktop_installer_macos.sh
./scripts/build_desktop_installer_macos.sh
```

The script fails closed with clear errors if ffmpeg, static UI, or the sidecar binary
is missing. It auto-downloads arm64 ffmpeg via `scripts/download_ffmpeg_macos.sh`.

Post-build verification (also runs from `build_macos_solo.sh`):

```bash
./scripts/verify_desktop_installer_macos.sh apps/desktop/release/qClip-mac-arm64.dmg
```

Expected artifact: `apps/desktop/release/qClip-mac-arm64.dmg`

First open of an unsigned app: **right-click → Open**.

## Signing & notarization (optional)

| Variable | Purpose |
|----------|---------|
| `CSC_LINK` / `CSC_KEY_PASSWORD` | `.p12` signing |
| `CSC_NAME` | Keychain identity instead of `CSC_LINK` |
| `APPLE_ID` / `APPLE_APP_SPECIFIC_PASSWORD` / `APPLE_TEAM_ID` | Notary password auth |
| `APPLE_API_KEY` / `APPLE_API_KEY_ID` / `APPLE_API_ISSUER` | Notary API key auth |

Unset → **unsigned** DMG (`CSC_IDENTITY_AUTO_DISCOVERY=false`). Manual notarize:

```bash
./scripts/notarize_macos_artifact.sh apps/desktop/release/qClip-mac-arm64.dmg
```

## Known gaps (scaffold vs Mac host)

| Item | Done without Mac | Still needs Mac host |
|------|------------------|----------------------|
| §5.1 VideoToolbox encode selection | ✅ `gpu_profile` / `export_video` + tests | Live encode smoke with bundled ffmpeg |
| §5.2 MPS Whisper / YOLO | ✅ device probe + auto fallback | arm64 Torch + CTranslate2 in sidecar |
| §5.3 Gatekeeper | Unsigned DMG + notarize script | Developer ID secrets in CI |
| DMG build | Scripts + CI job | Green `macos-installer` producing `.dmg` |

Full matrix: `packaging/installer/MACOS.md`.

## Related

- [Get qClip](BETA_DOWNLOAD.md) — end-user DMG path
- [Beta quickstart](BETA_TESTER_QUICKSTART.md)
- [ADR-001 Desktop packaging](ADR-001-desktop-packaging.md)
