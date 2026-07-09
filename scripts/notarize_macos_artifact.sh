#!/usr/bin/env bash
# Optional Apple notarization for macOS DMG/.app (§5).
#
# Skips cleanly when APPLE_* secrets are unset (unsigned beta path).
# Requires: xcrun notarytool, Developer ID cert via CSC_LINK/CSC_NAME.
#
# Usage:
#   ./scripts/notarize_macos_artifact.sh apps/desktop/release/StreamClip-mac-arm64.dmg

set -euo pipefail

ARTIFACT="${1:-}"
if [[ -z "$ARTIFACT" ]]; then
  echo "Usage: $0 <path-to-dmg-or-zip>" >&2
  exit 1
fi
if [[ ! -f "$ARTIFACT" ]]; then
  echo "ERROR: artifact not found: $ARTIFACT" >&2
  exit 1
fi

APPLE_ID="${APPLE_ID:-}"
APPLE_APP_PASSWORD="${APPLE_APP_SPECIFIC_PASSWORD:-}"
APPLE_TEAM_ID="${APPLE_TEAM_ID:-}"

if [[ -z "$APPLE_ID" || -z "$APPLE_APP_PASSWORD" || -z "$APPLE_TEAM_ID" ]]; then
  echo "NOTE: APPLE_ID / APPLE_APP_SPECIFIC_PASSWORD / APPLE_TEAM_ID unset — skipping notarization."
  echo "      DMG is installable via right-click → Open until notarized. See packaging/installer/MACOS.md"
  exit 0
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: notarization requires macOS host" >&2
  exit 1
fi

echo "=== Submitting $ARTIFACT for notarization ==="
SUBMIT_JSON="$(mktemp)"
trap 'rm -f "$SUBMIT_JSON"' EXIT

xcrun notarytool submit "$ARTIFACT" \
  --apple-id "$APPLE_ID" \
  --password "$APPLE_APP_PASSWORD" \
  --team-id "$APPLE_TEAM_ID" \
  --wait \
  --output-format json >"$SUBMIT_JSON"

STATUS="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('status',''))" "$SUBMIT_JSON")"
if [[ "$STATUS" != "Accepted" ]]; then
  echo "ERROR: notarization status=$STATUS (see $SUBMIT_JSON)" >&2
  exit 1
fi

echo "Notarization accepted. Stapling ticket..."
if [[ "$ARTIFACT" == *.dmg ]]; then
  xcrun stapler staple "$ARTIFACT"
fi

echo "notarize_macos_artifact: OK"
