#!/usr/bin/env bash
# Post-build checks for macOS desktop installer artifacts.
# Fails closed on missing UI / sidecar / ffmpeg / undersized DMG.
#
# Usage:
#   ./scripts/verify_desktop_installer_macos.sh [path/to/qClip-mac-arm64.dmg]
#
# Without a DMG path, verifies static UI + staged sidecar + bundled ffmpeg.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DMG="${1:-}"
EXPECTED_NAME="qClip-mac-arm64.dmg"

fail() {
  echo "VERIFY FAIL: $*" >&2
  exit 1
}

echo "=== verify_desktop_installer_macos ==="

[[ -f "$ROOT/static/ui/index.html" ]] || fail "static/ui/index.html missing"
[[ -d "$ROOT/static/ui/_next" ]] || fail "static/ui/_next missing"

# Repo-level ffmpeg (must exist before PyInstaller datas collect).
[[ -x "$ROOT/bin/ffmpeg/ffmpeg" ]] || fail "bin/ffmpeg/ffmpeg missing or not executable — run scripts/download_ffmpeg_macos.sh"
[[ -x "$ROOT/bin/ffmpeg/ffprobe" ]] || fail "bin/ffmpeg/ffprobe missing or not executable"

STAGING="$ROOT/apps/desktop/.staging/sidecar"
if [[ -d "$STAGING" ]]; then
  [[ -f "$STAGING/streamclip-sidecar" ]] || fail "staged sidecar binary missing ($STAGING/streamclip-sidecar)"
  [[ ! -f "$STAGING/streamclip-sidecar.exe" ]] || fail "Windows .exe found in macOS staging"
  # PyInstaller one-dir layout: binaries under bin/ffmpeg inside the staged tree.
  if [[ -x "$STAGING/bin/ffmpeg/ffmpeg" || -x "$STAGING/_internal/bin/ffmpeg/ffmpeg" ]]; then
    echo "Staged sidecar includes bundled ffmpeg"
  else
    # Soft warning only if tree exists but datas path differs — still fail if neither binary nor _internal.
    if [[ ! -d "$STAGING/_internal" ]]; then
      fail "staged sidecar looks incomplete (no _internal/ and no bin/ffmpeg/)"
    fi
    echo "NOTE: bundled ffmpeg path not found under staging (will rely on PyInstaller datas at runtime)"
  fi
else
  if [[ -n "$DMG" ]]; then
    echo "NOTE: apps/desktop/.staging/sidecar not present (DMG-only verify)"
  else
    fail "apps/desktop/.staging/sidecar missing — run build (or stage) before verify"
  fi
fi

if [[ -n "$DMG" ]]; then
  [[ -f "$DMG" ]] || fail "DMG not found: $DMG"
  BASE="$(basename "$DMG")"
  if [[ "$BASE" != "$EXPECTED_NAME" ]]; then
    echo "NOTE: expected artifact name $EXPECTED_NAME, got $BASE"
  fi
  DMG_MB=$(( $(wc -c < "$DMG") / 1024 / 1024 ))
  if (( DMG_MB < 50 )); then
    fail "DMG suspiciously small (${DMG_MB} MB) — bundle may be incomplete"
  fi
  echo "DMG OK: $DMG (${DMG_MB} MB)"

  # On a Mac host, mount and confirm .app + sidecar binary exist inside the DMG.
  if [[ "$(uname -s)" == "Darwin" ]] && command -v hdiutil >/dev/null 2>&1; then
    MNT="$(mktemp -d)"
    cleanup_mnt() {
      hdiutil detach "$MNT" -quiet 2>/dev/null || true
      rmdir "$MNT" 2>/dev/null || true
    }
    trap cleanup_mnt EXIT
    hdiutil attach "$DMG" -nobrowse -readonly -mountpoint "$MNT" >/dev/null
    APP="$(find "$MNT" -maxdepth 2 -name 'qClip.app' -type d | head -n 1 || true)"
    [[ -n "$APP" ]] || fail "qClip.app not found inside DMG"
    SIDECAR_IN_APP="$APP/Contents/Resources/sidecar/streamclip-sidecar"
    [[ -f "$SIDECAR_IN_APP" ]] || fail "sidecar binary missing inside .app: Resources/sidecar/streamclip-sidecar"
    [[ ! -f "${SIDECAR_IN_APP}.exe" ]] || fail "Windows .exe sidecar found inside .app"
    echo "DMG contents OK: qClip.app + sidecar"
    cleanup_mnt
    trap - EXIT
  fi
fi

echo "verify_desktop_installer_macos: all checks passed"
