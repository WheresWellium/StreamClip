#!/usr/bin/env bash
# Fetch published desktop installers into apps/desktop/release/ (collaborator auth).
# Used by Phase A/C of the desktop-solo gate — no Docker.
#
# Usage:
#   ./scripts/fetch_desktop_artifacts.sh
#   ./scripts/fetch_desktop_artifacts.sh v1.0.0-beta.5
#   ./scripts/fetch_desktop_artifacts.sh latest

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TAG="${1:-v1.0.0-beta.5}"
REPO="${STREAMCLIP_GITHUB_REPO:-WheresWellium/StreamClip}"
OUT="$ROOT/apps/desktop/release"
mkdir -p "$OUT"

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI (gh) required and authenticated." >&2
  exit 1
fi

echo "=== Fetch desktop artifacts ($TAG) from $REPO → $OUT ==="

fetch_pattern() {
  local pattern="$1"
  if [[ "$TAG" == "latest" ]]; then
    gh release download -R "$REPO" -p "$pattern" -D "$OUT" --clobber
  else
    gh release download "$TAG" -R "$REPO" -p "$pattern" -D "$OUT" --clobber
  fi
}

fetch_pattern "qClip-Setup-win-x64.exe" || {
  echo "ERROR: Windows installer not on release $TAG" >&2
  exit 1
}
fetch_pattern "latest.yml" || echo "NOTE: latest.yml missing (updater may not work)"

# macOS DMG may not exist yet — soft.
if fetch_pattern "qClip-mac-arm64.dmg" 2>/dev/null; then
  echo "macOS DMG fetched."
else
  echo "NOTE: qClip-mac-arm64.dmg not on $TAG — build with ./scripts/build_macos_solo.sh on Apple Silicon."
fi

echo ""
ls -lh "$OUT"/qClip-* "$OUT"/latest.yml 2>/dev/null || ls -lh "$OUT"
echo "Done."
