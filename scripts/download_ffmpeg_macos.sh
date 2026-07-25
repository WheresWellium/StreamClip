#!/usr/bin/env bash
# Download static ffmpeg + ffprobe for macOS desktop sidecar bundling.
# Places binaries in bin/ffmpeg/ (required by PyInstaller spec).
#
# Source: evermeet.cx static builds (GPL). Apple Silicon and Intel both use
# the same universal-capable static binaries for bundling.
#
# Usage:
#   ./scripts/download_ffmpeg_macos.sh
#   ./scripts/download_ffmpeg_macos.sh --force
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/bin/ffmpeg"
FORCE=0

for arg in "$@"; do
  case "$arg" in
    --force|-f) FORCE=1 ;;
    -h|--help)
      sed -n '2,14p' "$0"
      exit 0
      ;;
  esac
done

mkdir -p "$DEST"
FFMPEG="$DEST/ffmpeg"
FFPROBE="$DEST/ffprobe"

if [[ "$FORCE" -eq 0 && -x "$FFMPEG" && -x "$FFPROBE" ]]; then
  echo "ffmpeg binaries already present in bin/ffmpeg/ (use --force to re-download)."
  exit 0
fi

TMP="$(mktemp -d)"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

echo "Downloading ffmpeg + ffprobe (evermeet.cx static builds)..."
curl -fsSL -o "$TMP/ffmpeg.zip" "https://evermeet.cx/ffmpeg/getrelease/zip"
curl -fsSL -o "$TMP/ffprobe.zip" "https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip"

unzip -qo "$TMP/ffmpeg.zip" -d "$TMP"
unzip -qo "$TMP/ffprobe.zip" -d "$TMP"

if [[ ! -f "$TMP/ffmpeg" || ! -f "$TMP/ffprobe" ]]; then
  echo "ERROR: unexpected zip layout from evermeet.cx" >&2
  ls -la "$TMP" >&2
  exit 1
fi

cp "$TMP/ffmpeg" "$FFMPEG"
cp "$TMP/ffprobe" "$FFPROBE"
chmod +x "$FFMPEG" "$FFPROBE"

echo ""
echo "ffmpeg ready in bin/ffmpeg/"
"$FFMPEG" -version | head -n 1
"$FFPROBE" -version | head -n 1
