#!/usr/bin/env bash
# Phase C — build a tester zip with desktop installers (no Docker).
# Prefers apps/desktop/release/; fetches Windows exe via gh if missing.
#
# Usage:
#   ./scripts/package_desktop_solo_kit.sh
#   ./scripts/package_desktop_solo_kit.sh v1.0.0-beta.5

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TAG="${1:-v1.0.0-beta.5}"
STAMP="$(date +%Y%m%d-%H%M)"
COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
KIT_NAME="qclip-beta-kit-DesktopSolo-${COMMIT}-${STAMP}"
OUT_DIR="$ROOT/dist"
STAGE="$OUT_DIR/$KIT_NAME"
INSTALLERS="$STAGE/installers"

mkdir -p "$OUT_DIR"
rm -rf "$STAGE"
mkdir -p "$INSTALLERS"

RELEASE="$ROOT/apps/desktop/release"
WIN_EXE="$RELEASE/qClip-Setup-win-x64.exe"
MAC_DMG="$RELEASE/qClip-mac-arm64.dmg"

if [[ ! -f "$WIN_EXE" ]]; then
  echo "Windows installer missing — fetching..."
  chmod +x "$ROOT/scripts/fetch_desktop_artifacts.sh"
  "$ROOT/scripts/fetch_desktop_artifacts.sh" "$TAG"
fi
[[ -f "$WIN_EXE" ]] || { echo "ERROR: $WIN_EXE still missing" >&2; exit 1; }

cp -f "$WIN_EXE" "$INSTALLERS/"
[[ -f "$RELEASE/latest.yml" ]] && cp -f "$RELEASE/latest.yml" "$INSTALLERS/"
MAC_NOTE="macOS DMG: not included — run ./scripts/build_macos_solo.sh on Apple Silicon, then re-run this script."
if [[ -f "$MAC_DMG" ]]; then
  cp -f "$MAC_DMG" "$INSTALLERS/"
  MAC_NOTE="macOS: installers/qClip-mac-arm64.dmg — drag to Applications; unsigned → right-click Open."
fi

# Minimal docs for testers (desktop-only — no Docker instructions as primary).
for f in \
  docs/GET_STARTED.md \
  docs/BETA_KNOWN_ISSUES.md
do
  if [[ -f "$ROOT/$f" ]]; then
    mkdir -p "$STAGE/$(dirname "$f")"
    cp -f "$ROOT/$f" "$STAGE/$f"
  fi
done

cat > "$STAGE/KIT_README.txt" <<EOF
qClip desktop-solo beta kit
Generated: $(date -Iseconds)
Commit: $COMMIT
Tag: $TAG

THIS KIT IS DOCKER-FREE.
Install the desktop app for your OS — do not install Docker Desktop for this path.

Windows
-------
1. Run installers/qClip-Setup-win-x64.exe
2. SmartScreen (unsigned): More info → Run anyway
3. Start menu → qClip → Settings → License → paste invite key
4. Full guide: docs/GET_STARTED.md
   Or online: https://streamclip-henna.vercel.app/GET_STARTED/

macOS
-----
$MAC_NOTE

Logs
----
Windows: %LOCALAPPDATA%\\qClip\\logs\\
macOS:   ~/Library/Application Support/qClip/logs/

Repo (collaborators only): https://github.com/WheresWellium/StreamClip
EOF

ZIP="$OUT_DIR/${KIT_NAME}.zip"
rm -f "$ZIP"
( cd "$OUT_DIR" && zip -r -q "$ZIP" "$KIT_NAME" )

echo ""
echo "Desktop-solo kit ready:"
echo "  $ZIP"
echo "  Staging: $STAGE"
ls -lh "$INSTALLERS"
echo ""
echo "Distribute this zip via Drive / Lemon Squeezy / invite email (not public GitHub URLs)."
