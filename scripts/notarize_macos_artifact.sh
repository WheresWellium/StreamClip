#!/usr/bin/env bash
# Optional Apple notarization for macOS DMG/.app (§5.3).
#
# Skips cleanly when Apple credentials are unset (unsigned beta path).
# Requires: macOS host, xcrun notarytool, Developer ID–signed artifact.
#
# Auth (either set):
#   APPLE_ID + APPLE_APP_SPECIFIC_PASSWORD + APPLE_TEAM_ID
#   — or —
#   APPLE_API_KEY (path to .p8) + APPLE_API_KEY_ID + APPLE_API_ISSUER
#
# Usage:
#   ./scripts/notarize_macos_artifact.sh apps/desktop/release/qClip-mac-arm64.dmg

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
APPLE_API_KEY="${APPLE_API_KEY:-}"
APPLE_API_KEY_ID="${APPLE_API_KEY_ID:-}"
APPLE_API_ISSUER="${APPLE_API_ISSUER:-}"

password_auth=0
api_auth=0
[[ -n "$APPLE_ID" && -n "$APPLE_APP_PASSWORD" && -n "$APPLE_TEAM_ID" ]] && password_auth=1
[[ -n "$APPLE_API_KEY" && -n "$APPLE_API_KEY_ID" && -n "$APPLE_API_ISSUER" ]] && api_auth=1

if [[ "$password_auth" -eq 0 && "$api_auth" -eq 0 ]]; then
  echo "NOTE: Apple notarization credentials unset — skipping notarization."
  echo "      Set APPLE_ID + APPLE_APP_SPECIFIC_PASSWORD + APPLE_TEAM_ID"
  echo "      or APPLE_API_KEY + APPLE_API_KEY_ID + APPLE_API_ISSUER."
  echo "      Unsigned DMG: right-click → Open. See packaging/installer/MACOS.md"
  exit 0
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: notarization requires macOS host" >&2
  exit 1
fi

if ! command -v xcrun >/dev/null 2>&1; then
  echo "ERROR: xcrun not found — install Xcode Command Line Tools" >&2
  exit 1
fi

echo "=== Submitting $ARTIFACT for notarization ==="
SUBMIT_JSON="$(mktemp)"
trap 'rm -f "$SUBMIT_JSON"' EXIT

AUTH_ARGS=()
if [[ "$api_auth" -eq 1 ]]; then
  AUTH_ARGS=(--key "$APPLE_API_KEY" --key-id "$APPLE_API_KEY_ID" --issuer "$APPLE_API_ISSUER")
else
  AUTH_ARGS=(--apple-id "$APPLE_ID" --password "$APPLE_APP_PASSWORD" --team-id "$APPLE_TEAM_ID")
fi

xcrun notarytool submit "$ARTIFACT" \
  "${AUTH_ARGS[@]}" \
  --wait \
  --output-format json >"$SUBMIT_JSON"

STATUS="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('status',''))" "$SUBMIT_JSON")"
if [[ "$STATUS" != "Accepted" ]]; then
  echo "ERROR: notarization status=$STATUS" >&2
  python3 -c "import json,sys; print(json.dumps(json.load(open(sys.argv[1])), indent=2))" "$SUBMIT_JSON" >&2 || cat "$SUBMIT_JSON" >&2
  exit 1
fi

echo "Notarization accepted. Stapling ticket..."
if [[ "$ARTIFACT" == *.dmg || "$ARTIFACT" == *.app ]]; then
  xcrun stapler staple "$ARTIFACT"
  xcrun stapler validate "$ARTIFACT" || {
    echo "ERROR: stapler validate failed after staple" >&2
    exit 1
  }
fi

echo "notarize_macos_artifact: OK"
