# macOS installer — 30-minute builder runbook

**End users:** you do **not** need this page. Download the published DMG —
[Install → macOS](BETA_DOWNLOAD.md#macos).

**Builders:** this is the path to rebuild an unsigned `.dmg` (arm64 via CI escape
hatch, or universal locally). Notarization (Gatekeeper-clean) still needs an
Apple Developer ID.

Companion detail: `packaging/installer/MACOS.md` (repo root) ·
ADR: [`ADR-001-desktop-packaging.md`](ADR-001-desktop-packaging.md).

---

## Status

| Item | State |
|------|--------|
| electron-builder `mac` target `dmg` + `arch: ["universal"]` | ✅ Committed (`apps/desktop/package.json`) |
| Entitlements + hardenedRuntime | ✅ `apps/desktop/assets/entitlements.mac.plist` |
| Build script | ✅ `scripts/build_desktop_installer_macos.sh` |
| Verify script | ✅ `scripts/verify_desktop_installer_macos.sh` |
| Notarize script (skips if no Apple secrets) | ✅ `scripts/notarize_macos_artifact.sh` |
| CI arm64 on Latest | ✅ `STREAMCLIP_MAC_SINGLE_ARCH=arm64` via `desktop-release.yml` → `qClip-mac-arm64.dmg` on **v1.0.0-beta.23** |
| Universal on Latest | ☐ Local Mac with Rosetta + x86 Python → `qClip-mac-universal.dmg` |
| Notarized / Gatekeeper-clean | ❌ Needs Apple Developer Program |

Beta testers: use the [Apple Silicon DMG on Latest](BETA_DOWNLOAD.md#macos). On a Mac builder for universal:

```bash
./scripts/build_desktop_installer_macos.sh
# needs Rosetta + /usr/local x86_64 Python for the Intel sidecar half
gh release upload v1.0.0-beta.23 apps/desktop/release/qClip-mac-universal.dmg --clobber
```

CI (Apple Silicon only, no Rosetta):

```bash
gh workflow run desktop-release.yml -f version=1.0.0-beta.23 -f skip_windows=true
```

---

## 30-minute unsigned DMG (no Apple account)

### Prerequisites (once per Mac)

| Need | Check |
|------|--------|
| Apple Silicon Mac | Preferred; Intel not first-ship |
| macOS 12+ | — |
| Xcode CLT | `xcode-select --install` |
| Node.js 20+ | `node -v` |
| Python 3.11+ | `python3 --version` |
| ~15 GB free | Sidecar + Electron are large |

### Build

```bash
cd /path/to/streamclip
chmod +x scripts/build_desktop_installer_macos.sh \
         scripts/verify_desktop_installer_macos.sh \
         scripts/notarize_macos_artifact.sh \
         scripts/download_ffmpeg_macos.sh

./scripts/build_desktop_installer_macos.sh
```

Expected artifact: `apps/desktop/release/qClip-mac-arm64.dmg`

Post-build verify (also runs at end of build script):

```bash
./scripts/verify_desktop_installer_macos.sh apps/desktop/release/qClip-mac-arm64.dmg
```

First open of an **unsigned** app: **right-click → Open** (Gatekeeper).

### Timing budget

| Step | ~Minutes |
|------|----------|
| CLT / Node / Python if missing | 5–10 |
| `npm ci` + sidecar PyInstaller | 10–15 |
| electron-builder DMG | 5 |
| Verify + smoke open | 2 |
| **Total (warm machine)** | **~25–30** |

---

## Optional: Developer ID sign + notarize (~15 min more)

Requires Apple Developer Program membership.

| Variable | Purpose |
|----------|---------|
| `CSC_LINK` / `CSC_KEY_PASSWORD` | `.p12` Developer ID Application cert |
| `CSC_NAME` | Keychain identity instead of `CSC_LINK` |
| `APPLE_ID` | Apple ID email |
| `APPLE_APP_SPECIFIC_PASSWORD` | app-specific password (not account password) |
| `APPLE_TEAM_ID` | 10-char team id |

```bash
export CSC_LINK=/secure/DeveloperID.p12
export CSC_KEY_PASSWORD='…'
export APPLE_ID='you@example.com'
export APPLE_APP_SPECIFIC_PASSWORD='…'
export APPLE_TEAM_ID='XXXXXXXXXX'

./scripts/build_desktop_installer_macos.sh
./scripts/notarize_macos_artifact.sh apps/desktop/release/qClip-mac-arm64.dmg
```

Unset Apple vars → build stays unsigned; `notarize_macos_artifact.sh` exits 0 with a skip note
(safe for CI / borrowed Mac without a Developer ID).

---

## Known gaps (scaffold vs Mac host)

| Item | Done without Mac | Still needs Mac host |
|------|------------------|----------------------|
| §5.1 VideoToolbox encode selection | ✅ `gpu_profile` / `export_video` + tests | Bundle Darwin ffmpeg; live encode smoke |
| §5.2 MPS Whisper / YOLO | ✅ device probe + auto fallback | arm64 Torch + CTranslate2 in sidecar; MPS smoke |
| §5.3 Gatekeeper | Unsigned DMG script + notarize skip-path | Successful notarized arm64 `.dmg` |
| DMG build | Script + CI scaffold | Successful arm64 `.dmg` on a Mac |

Full matrix: `packaging/installer/MACOS.md`.

---

## Related

- [Install qClip](BETA_DOWNLOAD.md)
- [First clip](BETA_TESTER_QUICKSTART.md)
- [Windows EV signing](DESKTOP_SIGNING.md)
- [ADR-001 Desktop packaging](ADR-001-desktop-packaging.md)
