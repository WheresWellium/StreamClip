#!/usr/bin/env bash
# Build the qClip macOS desktop DMG (MASTER_TODO §5 / ADR-001).
#
# Pipeline: static UI -> PyInstaller sidecar(s) -> stage -> electron-builder --mac --universal.
# Requires a macOS host. Universal DMG needs BOTH arm64 + x64 sidecars (Rosetta + x86 Python on Apple Silicon).
#
# Usage:
#   ./scripts/build_desktop_installer_macos.sh
#   ./scripts/build_desktop_installer_macos.sh --skip-ui --skip-sidecar
#   STREAMCLIP_MAC_SINGLE_ARCH=arm64 ./scripts/build_desktop_installer_macos.sh   # escape hatch
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
SINGLE_ARCH="${STREAMCLIP_MAC_SINGLE_ARCH:-}"

signing_configured() {
  [[ -n "${CSC_LINK:-}" && -n "${CSC_KEY_PASSWORD:-}" ]] || [[ -n "${CSC_NAME:-}" ]]
}

host_electron_arch() {
  case "$(uname -m)" in
    arm64) echo "arm64" ;;
    x86_64) echo "x64" ;;
    *)
      echo "ERROR: unsupported uname -m=$(uname -m)" >&2
      exit 1
      ;;
  esac
}

# x86_64 Python under Rosetta (Homebrew /usr/local) for Intel sidecar on Apple Silicon.
find_x86_python() {
  if ! arch -x86_64 /usr/bin/true >/dev/null 2>&1; then
    return 1
  fi
  local c
  for c in \
    /usr/local/bin/python3.12 \
    /usr/local/bin/python3.11 \
    /usr/local/bin/python3.10 \
    /usr/local/bin/python3; do
    if [[ -x "$c" ]] && arch -x86_64 "$c" -c 'import struct; assert struct.calcsize("P") == 8' >/dev/null 2>&1; then
      # Reject arm64 binary mistakenly on PATH
      if arch -x86_64 "$c" -c 'import platform; assert platform.machine() == "x86_64"' >/dev/null 2>&1; then
        echo "$c"
        return 0
      fi
    fi
  done
  return 1
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
  echo "Preflight OK (host arch=$(host_electron_arch))"
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

build_and_stage_sidecar() {
  local electron_arch="$1"
  local py="$2"
  local use_rosetta="$3" # 1 or 0

  echo ""
  echo "=== PyInstaller sidecar ($electron_arch) ==="
  rm -rf "$SIDECAR_DIST"
  if [[ "$use_rosetta" == "1" ]]; then
    arch -x86_64 "$py" -m pip install -r requirements-desktop.txt -r requirements-packaging.txt -q
    arch -x86_64 "$py" -m PyInstaller packaging/pyinstaller/streamclip-sidecar.spec --noconfirm
  else
    "$py" -m pip install -r requirements-desktop.txt -r requirements-packaging.txt -q
    "$py" -m PyInstaller packaging/pyinstaller/streamclip-sidecar.spec --noconfirm
  fi

  if [[ ! -f "$SIDECAR_DIST/$SIDECAR_BIN_NAME" ]]; then
    echo "ERROR: Missing $SIDECAR_DIST/$SIDECAR_BIN_NAME after $electron_arch build." >&2
    exit 1
  fi
  if [[ -f "$SIDECAR_DIST/${SIDECAR_BIN_NAME}.exe" ]]; then
    echo "ERROR: Windows .exe sidecar on macOS host." >&2
    exit 1
  fi

  local dest="$STAGING/$electron_arch"
  rm -rf "$dest"
  mkdir -p "$dest"
  cp -R "$SIDECAR_DIST"/. "$dest"/
  rm -f "$dest/${SIDECAR_BIN_NAME}.exe"
  echo "Staged $electron_arch sidecar ($(du -sm "$dest" | awk '{print $1}') MB) -> $dest"
}

echo "=== qClip macOS desktop installer build (universal) ==="
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

# --- PyInstaller sidecar(s) ---
rm -rf "$STAGING"
mkdir -p "$STAGING"

if [[ "$SKIP_SIDECAR" -eq 0 ]]; then
  if [[ "${STREAMCLIP_SKIP_PYINSTALLER:-}" == "1" ]]; then
    echo "STREAMCLIP_SKIP_PYINSTALLER=1 — skipping PyInstaller (expect staged sidecars)."
  else
    HOST_EARCH="$(host_electron_arch)"
    if [[ -n "$SINGLE_ARCH" ]]; then
      echo "STREAMCLIP_MAC_SINGLE_ARCH=$SINGLE_ARCH — single-arch sidecar only (not a full universal runtime)."
      if [[ "$SINGLE_ARCH" == "x64" && "$HOST_EARCH" == "arm64" ]]; then
        X86_PY="$(find_x86_python || true)"
        [[ -n "$X86_PY" ]] || { echo "ERROR: x86_64 Python required under Rosetta (/usr/local/bin/python3)." >&2; exit 1; }
        build_and_stage_sidecar "x64" "$X86_PY" 1
      else
        build_and_stage_sidecar "$SINGLE_ARCH" "python3" 0
      fi
    else
      # Universal: need arm64 + x64 sidecars.
      if [[ "$HOST_EARCH" == "arm64" ]]; then
        build_and_stage_sidecar "arm64" "python3" 0
        X86_PY="$(find_x86_python || true)"
        if [[ -z "$X86_PY" ]]; then
          echo "" >&2
          echo "ERROR: Universal DMG needs an Intel (x86_64) sidecar as well." >&2
          echo "  1) softwareupdate --install-rosetta" >&2
          echo "  2) Install Homebrew into /usr/local under Rosetta, then:" >&2
          echo "       arch -x86_64 /usr/local/bin/brew install python@3.12" >&2
          echo "  3) Re-run this script." >&2
          echo "  Escape hatch (Apple Silicon only): STREAMCLIP_MAC_SINGLE_ARCH=arm64 $0" >&2
          exit 1
        fi
        build_and_stage_sidecar "x64" "$X86_PY" 1
      else
        # Intel Mac host: build x64 natively; arm64 sidecar cannot be produced here.
        build_and_stage_sidecar "x64" "python3" 0
        echo "" >&2
        echo "ERROR: Universal DMG needs an arm64 sidecar (build on Apple Silicon, or copy" >&2
        echo "       apps/desktop/.staging/sidecar/arm64 from an Apple Silicon build)." >&2
        echo "  Escape hatch (Intel only): STREAMCLIP_MAC_SINGLE_ARCH=x64 $0" >&2
        exit 1
      fi
    fi
  fi
else
  echo "Skipping sidecar build (--skip-sidecar)."
fi

# Validate staging layout
if [[ -n "$SINGLE_ARCH" ]]; then
  [[ -f "$STAGING/$SINGLE_ARCH/$SIDECAR_BIN_NAME" ]] \
    || { echo "ERROR: missing staged sidecar $STAGING/$SINGLE_ARCH/$SIDECAR_BIN_NAME" >&2; exit 1; }
else
  [[ -f "$STAGING/arm64/$SIDECAR_BIN_NAME" ]] \
    || { echo "ERROR: missing staged arm64 sidecar" >&2; exit 1; }
  [[ -f "$STAGING/x64/$SIDECAR_BIN_NAME" ]] \
    || { echo "ERROR: missing staged x64 sidecar" >&2; exit 1; }
fi
echo "Staged sidecar tree:"
du -sh "$STAGING"/* 2>/dev/null || true

if ! signing_configured; then
  echo ""
  echo "NOTE: No CSC_LINK/CSC_KEY_PASSWORD or CSC_NAME — DMG will be UNSIGNED."
  echo "      Gatekeeper will block until right-click → Open. See packaging/installer/MACOS.md."
  export CSC_IDENTITY_AUTO_DISCOVERY=false
  # Empty env vars (common when CI injects blank secrets) still trip electron-builder
  # into a codesign path that fails with "…/apps/desktop not a file".
  unset CSC_LINK CSC_KEY_PASSWORD CSC_NAME APPLE_ID APPLE_APP_SPECIFIC_PASSWORD APPLE_TEAM_ID || true
fi

if [[ "$SKIP_ELECTRON" -eq 1 ]]; then
  echo "Skipping electron-builder (--skip-electron-build)."
  exit 0
fi

echo ""
pushd "$DESKTOP_DIR" >/dev/null
if [[ ! -d node_modules ]]; then
  npm ci
fi
npm run build

# Prefer explicit --mac so Linux/Windows hosts never accidentally run this path.
# package.json defaults to universal; CLI --arm64 alone still merges to universal
# and then @electron/universal fails on identical sidecar dylibs. Force arch when
# STREAMCLIP_MAC_SINGLE_ARCH is set.
if [[ -n "$SINGLE_ARCH" ]]; then
  echo "=== Electron compile + macOS DMG ($SINGLE_ARCH only) ==="
  EB_ARCH="$SINGLE_ARCH"
  if [[ "$EB_ARCH" == "x64" ]]; then
    EB_ARCH="x64"
  fi
  node --input-type=commonjs -e '
  const fs = require("fs");
  const arch = process.argv[1];
  const path = "package.json";
  const pkg = JSON.parse(fs.readFileSync(path, "utf8"));
  pkg.build = pkg.build || {};
  pkg.build.mac = pkg.build.mac || {};
  pkg.build.mac.target = [{ target: "dmg", arch: [arch] }];
  fs.writeFileSync(path, JSON.stringify(pkg, null, 2) + "\n");
  console.log("Forced mac.target arch=", arch);
  ' "$EB_ARCH"
  npx electron-builder --mac "--${EB_ARCH}" --publish never
else
  echo "=== Electron compile + macOS DMG (universal) ==="
  npx electron-builder --mac --universal --publish never
fi
popd >/dev/null

DMG=""
shopt -s nullglob
for f in "$DESKTOP_DIR"/release/qClip-mac-universal.dmg \
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
echo "Stable URL after upload:"
echo "  https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-mac-universal.dmg"
echo "Docs: packaging/installer/MACOS.md"
