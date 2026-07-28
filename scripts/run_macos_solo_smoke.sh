#!/usr/bin/env bash
# Phase B — macOS solo smoke helper (no Docker). Run on Apple Silicon after DMG build.
#
# Usage:
#   ./scripts/run_macos_solo_smoke.sh
#   ./scripts/run_macos_solo_smoke.sh apps/desktop/release/qClip-mac-arm64.dmg

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DMG="${1:-apps/desktop/release/qClip-mac-arm64.dmg}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: macOS smoke requires a Mac host." >&2
  exit 1
fi

if [[ ! -f "$DMG" ]]; then
  echo "ERROR: DMG missing: $DMG" >&2
  echo "       Run: ./scripts/build_macos_solo.sh" >&2
  exit 1
fi

SHA="$(shasum -a 256 "$DMG" | awk '{print $1}')"
SIZE_MB=$(( $(wc -c < "$DMG") / 1024 / 1024 ))
echo "=== qClip macOS solo smoke ==="
echo "DMG:    $DMG"
echo "Size:   ${SIZE_MB} MB"
echo "SHA256: $SHA"
echo ""
echo "1. open \"$DMG\""
echo "2. Drag qClip to Applications"
echo "3. Unsigned: right-click → Open → Open"
echo "4. Complete docs/HUMAN_DESKTOP_SMOKE.md macOS steps"
echo ""
open "$DMG" || true
read -r -p "Press Enter after UI smoke steps 4–7..."

LOGDIR="$HOME/Library/Application Support/qClip/logs"
[[ -d "$LOGDIR" ]] || LOGDIR="$HOME/Library/Application Support/StreamClip/logs"
STAMP="$(date +%Y%m%d-%H%M%S)"
EVIDENCE_OUT="${STREAMCLIP_SMOKE_OUT:-$ROOT/tmp/desktop-solo-smoke-mac-$STAMP}"
mkdir -p "$EVIDENCE_OUT"
LOG_ZIP="$EVIDENCE_OUT/qclip-smoke-mac-logs.zip"

if [[ -d "$LOGDIR" ]]; then
  (cd "$(dirname "$LOGDIR")" && zip -r -q "$LOG_ZIP" "$(basename "$LOGDIR")")
  echo "Logs zipped: $LOG_ZIP"
else
  echo "WARNING: log dir not found ($LOGDIR). Launch qClip once, then re-run."
fi

read -r -p "Smoke result (PASS/FAIL): " RESULT
read -r -p "Notes (optional): " NOTES
COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"

cat > "$EVIDENCE_OUT/EVIDENCE.txt" <<EOF
# macOS solo smoke evidence
Date: $(date -Iseconds)
Host: $(uname -m) / $(sw_vers -productVersion 2>/dev/null || echo unknown)
Commit: $COMMIT
DMG: $DMG
SHA256: $SHA
SizeMB: $SIZE_MB
Result: $RESULT
Notes: $NOTES
LogZip: $LOG_ZIP
LogDir: $LOGDIR
EOF

echo ""
echo "Wrote $EVIDENCE_OUT/EVIDENCE.txt"
echo "Paste Result into docs/DESKTOP_SOLO_GATE.md Phase B evidence."
