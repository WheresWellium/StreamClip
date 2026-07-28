#!/usr/bin/env bash
# Phase D helper — bump docs + print merge/tag commands after A (+B) smoke PASS.
# Does NOT merge or push tags (requires human approval + gh write).
#
# Usage:
#   ./scripts/finish_desktop_solo_release.sh 1.0.0-beta.6
#   CONFIRM_SOLO_SMOKE=1 ./scripts/finish_desktop_solo_release.sh 1.0.0-beta.6

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VERSION="${1:-1.0.0-beta.6}"
TAG="v${VERSION#v}"
VERSION_NUM="${TAG#v}"

if [[ "${CONFIRM_SOLO_SMOKE:-}" != "1" ]]; then
  echo "Refusing to prepare release without CONFIRM_SOLO_SMOKE=1" >&2
  echo "Set that only after DESKTOP_SOLO_GATE Phase A (and B if shipping Mac) is PASS." >&2
  exit 1
fi

PKG="$ROOT/apps/desktop/package.json"
if [[ -f "$PKG" ]]; then
  node --input-type=commonjs -e "
  const fs = require('fs');
  const path = process.argv[1];
  const ver = process.argv[2];
  const pkg = JSON.parse(fs.readFileSync(path, 'utf8'));
  pkg.version = ver;
  fs.writeFileSync(path, JSON.stringify(pkg, null, 2) + '\n');
  console.log('Updated', path, '→', ver);
  " "$PKG" "$VERSION_NUM"
fi

BANNER_DATE="$(date +%Y-%m-%d)"
# Soft-touch BETA_DOWNLOAD banner if present
if [[ -f docs/BETA_DOWNLOAD.md ]]; then
  python3 - <<PY
from pathlib import Path
import re
p = Path("docs/BETA_DOWNLOAD.md")
text = p.read_text(encoding="utf-8")
text2, n = re.subn(
    r"(\*\*Current Windows installer:\*\* )\`[^\`]+\` \(\d{4}-\d{2}-\d{2}\)",
    r"\1\`$VERSION_NUM\` ($BANNER_DATE)",
    text,
    count=1,
)
if n:
    p.write_text(text2, encoding="utf-8")
    print(f"Updated BETA_DOWNLOAD banner → {('$VERSION_NUM')} ($BANNER_DATE)")
else:
    print("NOTE: BETA_DOWNLOAD banner pattern not matched — edit manually.")
PY
fi

echo ""
echo "=== Desktop solo release prep ($TAG) ==="
echo "1. Commit version bump if dirty"
echo "2. Merge PR #7 to master (gh pr merge 7 --merge) when checks green"
echo "3. Tag and push:"
echo "     git checkout master && git pull"
echo "     git tag $TAG"
echo "     git push origin $TAG"
echo "4. Confirm GitHub Release has qClip-Setup-win-x64.exe (+ DMG if built)"
echo "5. Redeploy henna MkDocs"
echo "6. ./scripts/package_desktop_solo_kit.sh $TAG"
echo ""
echo "Draft notes: docs/RELEASE_NOTES_beta.6.md"
