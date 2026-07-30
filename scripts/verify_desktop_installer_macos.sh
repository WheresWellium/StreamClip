#!/usr/bin/env bash
# Post-build checks for macOS desktop installer artifacts.
#
# Usage:
#   ./scripts/verify_desktop_installer_macos.sh [path/to/qClip-mac-universal.dmg]
#
# Without a DMG path, verifies static UI + staged sidecar only (pre-electron).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DMG="${1:-}"

fail() {
  echo "VERIFY FAIL: $*" >&2
  exit 1
}

echo "=== verify_desktop_installer_macos ==="

[[ -f "$ROOT/static/ui/index.html" ]] || fail "static/ui/index.html missing"
[[ -d "$ROOT/static/ui/_next" ]] || fail "static/ui/_next missing"

STAGING="$ROOT/apps/desktop/.staging/sidecar"
if [[ -d "$STAGING" ]]; then
  [[ ! -f "$STAGING/streamclip-sidecar.exe" ]] || fail "Windows .exe found in macOS staging"
  if [[ -f "$STAGING/arm64/streamclip-sidecar" || -f "$STAGING/x64/streamclip-sidecar" ]]; then
    # Universal dual-arch layout
    if [[ -d "$STAGING/arm64" ]]; then
      [[ -f "$STAGING/arm64/streamclip-sidecar" ]] || fail "arm64 sidecar binary missing"
    fi
    if [[ -d "$STAGING/x64" ]]; then
      [[ -f "$STAGING/x64/streamclip-sidecar" ]] || fail "x64 sidecar binary missing"
    fi
    echo "Staged dual-arch sidecar layout OK"
  elif [[ -f "$STAGING/streamclip-sidecar" ]]; then
    echo "NOTE: legacy flat sidecar layout (arm64-only beta)"
  else
    fail "staged sidecar binary missing (expected sidecar/{arm64,x64}/streamclip-sidecar)"
  fi
else
  echo "NOTE: apps/desktop/.staging/sidecar not present (run stage step or full build)"
fi

if [[ -n "$DMG" ]]; then
  [[ -f "$DMG" ]] || fail "DMG not found: $DMG"
  DMG_MB=$(( $(wc -c < "$DMG") / 1024 / 1024 ))
  if (( DMG_MB < 50 )); then
    fail "DMG suspiciously small (${DMG_MB} MB)"
  fi
  echo "DMG OK: $DMG (${DMG_MB} MB)"
fi

echo "verify_desktop_installer_macos: all checks passed"
