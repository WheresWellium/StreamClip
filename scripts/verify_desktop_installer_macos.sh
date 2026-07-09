#!/usr/bin/env bash
# Post-build checks for macOS desktop installer artifacts.
#
# Usage:
#   ./scripts/verify_desktop_installer_macos.sh [path/to/StreamClip-mac-arm64.dmg]
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
  [[ -f "$STAGING/streamclip-sidecar" ]] || fail "staged sidecar binary missing"
  [[ ! -f "$STAGING/streamclip-sidecar.exe" ]] || fail "Windows .exe found in macOS staging"
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
