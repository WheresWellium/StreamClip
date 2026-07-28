#!/usr/bin/env bash
# One-command operator path: build + verify qClip-mac-arm64.dmg on a solo Mac.
#
# Usage (from repo root, Apple Silicon):
#   ./scripts/build_macos_solo.sh
#   ./scripts/build_macos_solo.sh --skip-ui   # forwarded to build_desktop_installer_macos.sh
#
# Next: Finder smoke (docs/HUMAN_DESKTOP_SMOKE.md) then copy DMG into the invite kit.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DMG="apps/desktop/release/qClip-mac-arm64.dmg"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: macOS solo DMG build requires a Mac host (uname=$(uname -s))." >&2
  echo "       Docs: docs/MACOS_INSTALLER.md" >&2
  exit 1
fi

echo "=== qClip macOS solo DMG ==="
echo ""
echo "Prerequisites (fail the build if missing):"
echo "  • Apple Silicon Mac (arm64) — product artifact is qClip-mac-arm64.dmg"
echo "  • Xcode Command Line Tools — xcode-select --install"
echo "  • Node.js 20+ and npm"
echo "  • Python 3.11+"
echo "  • ~15 GB free disk"
echo "  • Signing optional — unset CSC_* / Apple notary env → unsigned DMG"
echo ""
echo "Details: docs/MACOS_INSTALLER.md"
echo ""

chmod +x \
  "$ROOT/scripts/build_desktop_installer_macos.sh" \
  "$ROOT/scripts/verify_desktop_installer_macos.sh" \
  2>/dev/null || true

echo "=== Build ==="
./scripts/build_desktop_installer_macos.sh "$@"

echo ""
echo "=== Verify ==="
./scripts/verify_desktop_installer_macos.sh "$DMG"

echo ""
echo "=== Done ==="
echo "Artifact: $ROOT/$DMG"
echo ""
echo "Next steps:"
echo "  1. Finder smoke — docs/HUMAN_DESKTOP_SMOKE.md (macOS section):"
echo "       open DMG → drag to Applications → right-click Open if unsigned →"
echo "       splash → license → short job → play clip → check logs"
echo "  2. Copy into invite kit:"
echo "       cp \"$DMG\" <kit>/installers/qClip-mac-arm64.dmg"
echo "       Or on Windows after Mac build is available:"
echo "       .\\scripts\\prepare_beta_kit.ps1 -IncludeInstaller"
echo "       (picks up apps/desktop/release/qClip-mac-arm64.dmg when present)"
echo ""
