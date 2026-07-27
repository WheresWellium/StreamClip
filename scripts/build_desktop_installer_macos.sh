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
#   CSC_IDENTITY_AUTO_DISCOVERY=false is set automatically when no cert is configured

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SKIP_UI=0
SKIP_SIDECAR=0
SKIP_ELECTRON=0

for arg in "$@"; do
  case "$arg" in
    --skip-ui) SKIP_UI=1 ;;
    --skip-sidecar) SKIP_SIDECAR=1 ;;
    --skip-electron-build) SKIP_ELECTRON=1 ;;
    -h|--help)
      sed -n '2,20p' "$0"
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

DESKTOP_DIR="$ROOT/apps/desktop"
SIDECAR_DIST="$ROOT/dist/streamclip-sidecar"
STAGING="$DESKTOP_DIR/.staging/sidecar"
SIDECAR_BIN_NAME="streamclip-sidecar"

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
  if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: Python 3.11+ required" >&2
    missing=1
  fi
  if ! xcode-select -p >/dev/null 2>&1; then
    echo "ERROR: Xcode Command Line Tools required (xcode-select --install)" >&2
    missing=1
  fi
  if [[ ! -f "$ROOT/apps/desktop/assets/entitlements.mac.plist" ]]; then
    echo "ERROR: Missing apps/desktop/assets/entitlements.mac.plist" >&2
    missing=1
  fi
  if (( missing )); then exit 1; fi
  echo "Preflight OK"
}

verify_static_ui() {
  if [[ ! -f "$ROOT/static/ui/index.html" ]]; then
    echo "ERROR: static/ui/index.html missing — UI build failed or was skipped." >&2
    exit 1
  fi
  if [[ ! -d "$ROOT/static/ui/_next" ]]; then
    echo "ERROR: static/ui/_next missing — export incomplete." >&2
    exit 1
  fi
  echo "Static UI OK ($(du -sh "$ROOT/static/ui" | awk '{print $1}'))"
}

echo "=== qClip macOS desktop installer build ==="
echo "Arch preference: arm64 (Apple Silicon first; universal2 later — §5.5)"
preflight

# --- ffmpeg (Darwin) ---
if [[ ! -x "$ROOT/bin/ffmpeg/ffmpeg" || ! -x "$ROOT/bin/ffmpeg/ffprobe" ]]; then
  echo ""
  echo "=== ffmpeg binaries missing — downloading ==="
  chmod +x "$ROOT/scripts/download_ffmpeg_macos.sh"
  "$ROOT/scripts/download_ffmpeg_macos.sh"
fi
if [[ ! -x "$ROOT/bin/ffmpeg/ffmpeg" || ! -x "$ROOT/bin/ffmpeg/ffprobe" ]]; then
  echo "ERROR: bin/ffmpeg/ffmpeg and ffprobe required before sidecar build." >&2
  exit 1
fi

# --- Static UI ---
if [[ "$SKIP_UI" -eq 0 ]]; then
  echo ""
  echo "=== Static UI ==="
  if [[ -f "$ROOT/scripts/build_desktop_ui.sh" ]]; then
    chmod +x "$ROOT/scripts/build_desktop_ui.sh"
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
    echo "STREAMCLIP_SKIP_PYINSTALLER=1 — skipping PyInstaller."
  else
    if ! command -v pyinstaller >/dev/null 2>&1; then
      echo "Installing desktop + packaging requirements..."
      python3 -m pip install -r requirements-desktop.txt -r requirements-packaging.txt -q
    fi
    python3 -m PyInstaller packaging/pyinstaller/streamclip-sidecar.spec --noconfirm
  fi
else
  echo "Skipping sidecar build (--skip-sidecar)."
fi

# --- Stage sidecar (Darwin binary name, no .exe) ---
echo ""
echo "=== Stage sidecar for Electron ==="
if [[ ! -d "$SIDECAR_DIST" ]]; then
  echo "ERROR: Missing $SIDECAR_DIST — build sidecar first (or drop --skip-sidecar)." >&2
  exit 1
fi

# Prefer bare binary; accept .exe only if somehow present (cross-copy mistake).
if [[ -f "$SIDECAR_DIST/$SIDECAR_BIN_NAME" ]]; then
  :
elif [[ -f "$SIDECAR_DIST/${SIDECAR_BIN_NAME}.exe" ]]; then
  echo "ERROR: Found Windows .exe sidecar on macOS host. Rebuild with PyInstaller on Darwin." >&2
  exit 1
else
  echo "ERROR: Missing $SIDECAR_DIST/$SIDECAR_BIN_NAME" >&2
  exit 1
fi

rm -rf "$STAGING"
mkdir -p "$STAGING"
cp -R "$SIDECAR_DIST"/. "$STAGING"/
# Never ship a Windows exe into the .app bundle.
rm -f "$STAGING/${SIDECAR_BIN_NAME}.exe"
STAGED_MB=$(du -sm "$STAGING" | awk '{print $1}')
echo "Staged sidecar (${STAGED_MB} MB) -> apps/desktop/.staging/sidecar/"

if ! signing_configured; then
  echo ""
  echo "NOTE: No CSC_LINK/CSC_KEY_PASSWORD or CSC_NAME — DMG will be UNSIGNED."
  echo "      Gatekeeper will block until right-click → Open. See packaging/installer/MACOS.md."
  export CSC_IDENTITY_AUTO_DISCOVERY=false
fi

if [[ "$SKIP_ELECTRON" -eq 1 ]]; then
  echo "Skipping electron-builder (--skip-electron-build)."
  exit 0
fi

echo ""
echo "=== Electron compile + macOS DMG (arm64) ==="
pushd "$DESKTOP_DIR" >/dev/null
if [[ ! -d node_modules ]]; then
  npm ci
fi
npm run build
# Prefer explicit --mac so Linux/Windows hosts never accidentally run this path.
npx electron-builder --mac --arm64 --publish never
popd >/dev/null

DMG=""
shopt -s nullglob
for f in "$DESKTOP_DIR"/release/qClip-mac-arm64.dmg \
         "$DESKTOP_DIR"/release/qClip-mac-*.dmg; do
  if [[ -f "$f" ]]; then
    DMG="$f"
    break
  fi
done
shopt -u nullglob

if [[ -n "$DMG" ]]; then
  DMG_MB=$(( $(wc -c < "$DMG") / 1024 / 1024 ))
  echo ""
  echo "Installer ready: $DMG (${DMG_MB} MB)"
  if signing_configured; then
    echo "Signing identity configured (CSC_* / CSC_NAME)."
  fi
  if [[ -x "$ROOT/scripts/verify_desktop_installer_macos.sh" ]]; then
    echo ""
    "$ROOT/scripts/verify_desktop_installer_macos.sh" "$DMG"
  fi
  if [[ -x "$ROOT/scripts/notarize_macos_artifact.sh" ]]; then
    echo ""
    "$ROOT/scripts/notarize_macos_artifact.sh" "$DMG"
  fi
else
  echo "electron-builder finished but no qClip-mac-*.dmg under apps/desktop/release/" >&2
  exit 1
fi

echo ""
echo "Docs: packaging/installer/MACOS.md"
