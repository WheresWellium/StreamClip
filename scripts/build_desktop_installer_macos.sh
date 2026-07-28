#!/usr/bin/env bash
# Build the qClip macOS desktop DMG (MASTER_TODO §5 / ADR-001).
#
# Pipeline: static UI -> PyInstaller sidecar -> stage (no .exe) -> electron-builder --mac.
# Requires a macOS host (Apple Silicon preferred; arm64-first per §5.5).
# Code signing / notarization (optional): see packaging/installer/MACOS.md.
#
# Usage:
#   ./scripts/build_desktop_installer_macos.sh
#   ./scripts/build_desktop_installer_macos.sh --skip-ui --skip-sidecar
#   STREAMCLIP_SKIP_PYINSTALLER=1 ./scripts/build_desktop_installer_macos.sh
#
# Env (signing — fail soft when unset):
#   CSC_LINK / CSC_KEY_PASSWORD     — or macOS keychain identity via CSC_NAME
#   APPLE_ID / APPLE_APP_SPECIFIC_PASSWORD / APPLE_TEAM_ID — notarization
#   (or APPLE_API_KEY / APPLE_API_KEY_ID / APPLE_API_ISSUER)
#   CSC_IDENTITY_AUTO_DISCOVERY=false is set automatically when no cert is configured
#
# Fails closed if ffmpeg, static UI, or sidecar binary is missing.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SKIP_UI=0
SKIP_SIDECAR=0
SKIP_ELECTRON=0
EXPECTED_DMG_NAME="qClip-mac-arm64.dmg"

for arg in "$@"; do
  case "$arg" in
    --skip-ui) SKIP_UI=1 ;;
    --skip-sidecar) SKIP_SIDECAR=1 ;;
    --skip-electron-build) SKIP_ELECTRON=1 ;;
    -h|--help)
      sed -n '2,22p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: macOS DMG build requires a Mac host (uname=$(uname -s))." >&2
  echo "       Scaffold docs: packaging/installer/MACOS.md" >&2
  exit 1
fi

HOST_ARCH="$(uname -m)"
if [[ "$HOST_ARCH" != "arm64" && "${STREAMCLIP_ALLOW_NON_ARM64:-}" != "1" ]]; then
  echo "ERROR: host arch is $HOST_ARCH; product DMG is arm64-only (qClip-mac-arm64.dmg)." >&2
  echo "       Build on Apple Silicon, or set STREAMCLIP_ALLOW_NON_ARM64=1 to override." >&2
  exit 1
fi

DESKTOP_DIR="$ROOT/apps/desktop"
SIDECAR_DIST="$ROOT/dist/streamclip-sidecar"
STAGING="$DESKTOP_DIR/.staging/sidecar"
SIDECAR_BIN_NAME="streamclip-sidecar"
EXPECTED_DMG="$DESKTOP_DIR/release/$EXPECTED_DMG_NAME"

chmod +x \
  "$ROOT/scripts/download_ffmpeg_macos.sh" \
  "$ROOT/scripts/build_desktop_ui.sh" \
  "$ROOT/scripts/verify_desktop_installer_macos.sh" \
  "$ROOT/scripts/notarize_macos_artifact.sh" \
  2>/dev/null || true

signing_configured() {
  [[ -n "${CSC_LINK:-}" && -n "${CSC_KEY_PASSWORD:-}" ]] || [[ -n "${CSC_NAME:-}" ]]
}

preflight() {
  echo "=== Preflight ==="
  local missing=0
  if ! command -v node >/dev/null 2>&1; then
    echo "ERROR: Node.js 20+ required (nodejs.org or brew install node)" >&2
    missing=1
  fi
  if ! command -v npm >/dev/null 2>&1; then
    echo "ERROR: npm required (ships with Node.js)" >&2
    missing=1
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: Python 3.11+ required" >&2
    missing=1
  fi
  if ! xcode-select -p >/dev/null 2>&1; then
    echo "ERROR: Xcode Command Line Tools required (xcode-select --install)" >&2
    missing=1
  fi
  if [[ ! -f "$ROOT/apps/desktop/package.json" ]]; then
    echo "ERROR: Missing apps/desktop/package.json" >&2
    missing=1
  fi
  if [[ ! -f "$ROOT/apps/desktop/assets/entitlements.mac.plist" ]]; then
    echo "ERROR: Missing apps/desktop/assets/entitlements.mac.plist" >&2
    missing=1
  fi
  if [[ ! -f "$ROOT/packaging/pyinstaller/streamclip-sidecar.spec" ]]; then
    echo "ERROR: Missing packaging/pyinstaller/streamclip-sidecar.spec" >&2
    missing=1
  fi
  if (( missing )); then exit 1; fi
  echo "Preflight OK (host=$HOST_ARCH)"
}

require_ffmpeg() {
  if [[ ! -x "$ROOT/bin/ffmpeg/ffmpeg" || ! -x "$ROOT/bin/ffmpeg/ffprobe" ]]; then
    echo "ERROR: bin/ffmpeg/ffmpeg and ffprobe required (executable)." >&2
    echo "       Run: ./scripts/download_ffmpeg_macos.sh" >&2
    exit 1
  fi
}

verify_static_ui() {
  if [[ ! -f "$ROOT/static/ui/index.html" ]]; then
    echo "ERROR: static/ui/index.html missing — UI build failed or was skipped." >&2
    echo "       Run without --skip-ui, or: ./scripts/build_desktop_ui.sh" >&2
    exit 1
  fi
  if [[ ! -d "$ROOT/static/ui/_next" ]]; then
    echo "ERROR: static/ui/_next missing — export incomplete." >&2
    exit 1
  fi
  echo "Static UI OK ($(du -sh "$ROOT/static/ui" | awk '{print $1}'))"
}

require_sidecar_dist() {
  if [[ ! -d "$SIDECAR_DIST" ]]; then
    echo "ERROR: Missing $SIDECAR_DIST — build sidecar first (drop --skip-sidecar)." >&2
    exit 1
  fi
  if [[ -f "$SIDECAR_DIST/${SIDECAR_BIN_NAME}.exe" && ! -f "$SIDECAR_DIST/$SIDECAR_BIN_NAME" ]]; then
    echo "ERROR: Found Windows .exe sidecar on macOS host. Rebuild with PyInstaller on Darwin." >&2
    exit 1
  fi
  if [[ ! -f "$SIDECAR_DIST/$SIDECAR_BIN_NAME" ]]; then
    echo "ERROR: Missing $SIDECAR_DIST/$SIDECAR_BIN_NAME" >&2
    exit 1
  fi
  if [[ ! -x "$SIDECAR_DIST/$SIDECAR_BIN_NAME" ]]; then
    chmod +x "$SIDECAR_DIST/$SIDECAR_BIN_NAME" || true
  fi
}

echo "=== qClip macOS desktop installer build ==="
echo "Arch preference: arm64 (Apple Silicon first; universal2 later — §5.5)"
echo "Expected artifact: apps/desktop/release/$EXPECTED_DMG_NAME"
preflight

# --- ffmpeg (Darwin arm64) ---
if [[ ! -x "$ROOT/bin/ffmpeg/ffmpeg" || ! -x "$ROOT/bin/ffmpeg/ffprobe" ]]; then
  echo ""
  echo "=== ffmpeg binaries missing — downloading ==="
  "$ROOT/scripts/download_ffmpeg_macos.sh"
fi
require_ffmpeg

# --- Static UI ---
if [[ "$SKIP_UI" -eq 0 ]]; then
  echo ""
  echo "=== Static UI ==="
  if [[ -f "$ROOT/scripts/build_desktop_ui.sh" ]]; then
    "$ROOT/scripts/build_desktop_ui.sh"
  elif [[ -f "$ROOT/scripts/build_desktop_ui.ps1" ]] && command -v pwsh >/dev/null 2>&1; then
    pwsh -File "$ROOT/scripts/build_desktop_ui.ps1"
  else
    echo "ERROR: static UI build script missing and no fallback." >&2
    exit 1
  fi
else
  echo "Skipping static UI build (--skip-ui)."
fi
verify_static_ui

# --- PyInstaller sidecar ---
if [[ "$SKIP_SIDECAR" -eq 0 ]]; then
  echo ""
  echo "=== PyInstaller sidecar ==="
  if [[ "${STREAMCLIP_SKIP_PYINSTALLER:-}" == "1" ]]; then
    echo "STREAMCLIP_SKIP_PYINSTALLER=1 — skipping PyInstaller (require existing dist)."
    require_sidecar_dist
  else
    if ! python3 -c "import PyInstaller" >/dev/null 2>&1; then
      echo "Installing desktop + packaging requirements..."
      python3 -m pip install -r requirements-desktop.txt -r requirements-packaging.txt -q
    fi
    python3 -m PyInstaller packaging/pyinstaller/streamclip-sidecar.spec --noconfirm
    require_sidecar_dist
  fi
else
  echo "Skipping sidecar build (--skip-sidecar)."
  require_sidecar_dist
fi

# --- Stage sidecar (Darwin binary name, no .exe) ---
echo ""
echo "=== Stage sidecar for Electron ==="
require_sidecar_dist

rm -rf "$STAGING"
mkdir -p "$STAGING"
cp -R "$SIDECAR_DIST"/. "$STAGING"/
# Never ship a Windows exe into the .app bundle.
rm -f "$STAGING/${SIDECAR_BIN_NAME}.exe"
[[ -f "$STAGING/$SIDECAR_BIN_NAME" ]] || {
  echo "ERROR: staged sidecar binary missing after copy" >&2
  exit 1
}
chmod +x "$STAGING/$SIDECAR_BIN_NAME" || true
STAGED_MB=$(du -sm "$STAGING" | awk '{print $1}')
if (( STAGED_MB < 20 )); then
  echo "ERROR: staged sidecar suspiciously small (${STAGED_MB} MB)" >&2
  exit 1
fi
echo "Staged sidecar (${STAGED_MB} MB) -> apps/desktop/.staging/sidecar/"

if ! signing_configured; then
  echo ""
  echo "NOTE: No CSC_LINK/CSC_KEY_PASSWORD or CSC_NAME — DMG will be UNSIGNED."
  echo "      Gatekeeper: right-click qClip.app → Open (first launch)."
  echo "      Docs: packaging/installer/MACOS.md"
  # Empty GitHub Actions secrets still inject CSC_LINK=""; clear so electron-builder
  # does not attempt codesign against a non-file path.
  unset CSC_LINK CSC_KEY_PASSWORD CSC_NAME || true
  export CSC_IDENTITY_AUTO_DISCOVERY=false
fi

# Fail closed if ffmpeg never made it into the staged PyInstaller tree.
if ! find "$STAGING" -type f \( -name 'ffmpeg' -o -name 'ffmpeg.exe' \) | grep -q .; then
  echo "ERROR: staged sidecar is missing ffmpeg — re-run download_ffmpeg_macos.sh and rebuild sidecar." >&2
  exit 1
fi
if ! find "$STAGING" -type f \( -name 'ffprobe' -o -name 'ffprobe.exe' \) | grep -q .; then
  echo "ERROR: staged sidecar is missing ffprobe — re-run download_ffmpeg_macos.sh and rebuild sidecar." >&2
  exit 1
fi

if [[ "$SKIP_ELECTRON" -eq 1 ]]; then
  echo "Skipping electron-builder (--skip-electron-build)."
  "$ROOT/scripts/verify_desktop_installer_macos.sh" || exit 1
  exit 0
fi

echo ""
echo "=== Electron compile + macOS DMG (arm64) ==="
pushd "$DESKTOP_DIR" >/dev/null
if [[ ! -d node_modules/electron ]] || [[ ! -d node_modules/electron-builder ]]; then
  npm ci
fi
npm run build
[[ -f dist/main.js ]] || {
  echo "ERROR: apps/desktop/dist/main.js missing after tsc — Electron shell did not compile." >&2
  exit 1
}
# Prefer explicit --mac --arm64 so the artifact name stays qClip-mac-arm64.dmg.
# When unsigned, force identity=null — CSC_IDENTITY_AUTO_DISCOVERY=false alone is
# not enough if empty CSC_* leaked in (electron-builder → "<workdir> not a file").
EB_EXTRA=()
if ! signing_configured; then
  unset CSC_LINK CSC_KEY_PASSWORD CSC_NAME || true
  export CSC_IDENTITY_AUTO_DISCOVERY=false
  EB_EXTRA+=(-c.mac.identity=null)
fi
npx electron-builder --mac --arm64 --publish never "${EB_EXTRA[@]}"
popd >/dev/null

if [[ ! -f "$EXPECTED_DMG" ]]; then
  echo "ERROR: expected DMG missing: $EXPECTED_DMG" >&2
  echo "       electron-builder finished but artifactName did not match qClip-mac-{arch}.dmg" >&2
  ls -la "$DESKTOP_DIR/release" 2>/dev/null || true
  exit 1
fi

DMG_MB=$(( $(wc -c < "$EXPECTED_DMG") / 1024 / 1024 ))
echo ""
echo "Installer ready: $EXPECTED_DMG (${DMG_MB} MB)"
if signing_configured; then
  echo "Signing identity configured (CSC_* / CSC_NAME)."
fi

echo ""
"$ROOT/scripts/verify_desktop_installer_macos.sh" "$EXPECTED_DMG"

echo ""
"$ROOT/scripts/notarize_macos_artifact.sh" "$EXPECTED_DMG"

echo ""
echo "Done: $EXPECTED_DMG"
echo "Docs: packaging/installer/MACOS.md · docs/MACOS_INSTALLER.md"
