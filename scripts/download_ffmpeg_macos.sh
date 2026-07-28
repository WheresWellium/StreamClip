#!/usr/bin/env bash
# Download static ffmpeg + ffprobe for macOS desktop sidecar bundling.
# Places binaries in bin/ffmpeg/ (required by PyInstaller spec).
#
# Prefer Apple Silicon (arm64) — product path is qClip-mac-arm64.dmg (§5.5).
# Source: ffmpeg.martin-riedl.de (static macOS arm64/amd64 builds with VideoToolbox).
# Note: evermeet.cx is Intel-only and is NOT used.
#
# Usage:
#   ./scripts/download_ffmpeg_macos.sh
#   ./scripts/download_ffmpeg_macos.sh --force
#   STREAMCLIP_FFMPEG_MAC_ARCH=amd64 ./scripts/download_ffmpeg_macos.sh --force
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/bin/ffmpeg"
FORCE=0
# Product default: arm64. Override only for experimental Intel builds.
ARCH="${STREAMCLIP_FFMPEG_MAC_ARCH:-arm64}"
CHANNEL="${STREAMCLIP_FFMPEG_MAC_CHANNEL:-release}"

for arg in "$@"; do
  case "$arg" in
    --force|-f) FORCE=1 ;;
    --amd64|--x86_64) ARCH=amd64 ;;
    --arm64) ARCH=arm64 ;;
    -h|--help)
      sed -n '2,16p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

case "$ARCH" in
  arm64|aarch64) ARCH=arm64 ;;
  amd64|x86_64|x64) ARCH=amd64 ;;
  *)
    echo "ERROR: unsupported STREAMCLIP_FFMPEG_MAC_ARCH=$ARCH (use arm64 or amd64)" >&2
    exit 1
    ;;
esac

mkdir -p "$DEST"
FFMPEG="$DEST/ffmpeg"
FFPROBE="$DEST/ffprobe"

if [[ "$FORCE" -eq 0 && -x "$FFMPEG" && -x "$FFPROBE" ]]; then
  echo "ffmpeg binaries already present in bin/ffmpeg/ (use --force to re-download)."
  exit 0
fi

BASE="https://ffmpeg.martin-riedl.de/redirect/latest/macos/${ARCH}/${CHANNEL}"
FFMPEG_URL="${BASE}/ffmpeg.zip"
FFPROBE_URL="${BASE}/ffprobe.zip"

TMP="$(mktemp -d)"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

echo "Downloading ffmpeg + ffprobe (martin-riedl.de static macOS ${ARCH}/${CHANNEL})..."
echo "  $FFMPEG_URL"
echo "  $FFPROBE_URL"
if ! curl -fsSL -o "$TMP/ffmpeg.zip" "$FFMPEG_URL"; then
  echo "ERROR: failed to download ffmpeg.zip from $FFMPEG_URL" >&2
  exit 1
fi
if ! curl -fsSL -o "$TMP/ffprobe.zip" "$FFPROBE_URL"; then
  echo "ERROR: failed to download ffprobe.zip from $FFPROBE_URL" >&2
  exit 1
fi

unzip -qo "$TMP/ffmpeg.zip" -d "$TMP/ffmpeg_out"
unzip -qo "$TMP/ffprobe.zip" -d "$TMP/ffprobe_out"

find_bin() {
  local name="$1" dir="$2"
  if [[ -f "$dir/$name" ]]; then
    echo "$dir/$name"
    return 0
  fi
  local found
  found="$(find "$dir" -type f -name "$name" | head -n 1 || true)"
  if [[ -n "$found" ]]; then
    echo "$found"
    return 0
  fi
  return 1
}

SRC_FFMPEG="$(find_bin ffmpeg "$TMP/ffmpeg_out")" || {
  echo "ERROR: unexpected zip layout — ffmpeg binary missing" >&2
  find "$TMP/ffmpeg_out" -maxdepth 3 -type f >&2 || true
  exit 1
}
SRC_FFPROBE="$(find_bin ffprobe "$TMP/ffprobe_out")" || {
  echo "ERROR: unexpected zip layout — ffprobe binary missing" >&2
  find "$TMP/ffprobe_out" -maxdepth 3 -type f >&2 || true
  exit 1
}

# Fail closed if we got the wrong Mach-O arch (common with Intel-only mirrors).
if command -v file >/dev/null 2>&1; then
  FT="$(file -b "$SRC_FFMPEG" || true)"
  case "$ARCH" in
    arm64)
      if ! grep -qiE 'arm64|aarch64' <<<"$FT"; then
        echo "ERROR: expected arm64 Mach-O ffmpeg, got: $FT" >&2
        echo "       Refusing Intel-only binaries for Apple Silicon product builds." >&2
        exit 1
      fi
      ;;
    amd64)
      if ! grep -qiE 'x86_64|x86-64' <<<"$FT"; then
        echo "ERROR: expected x86_64 Mach-O ffmpeg, got: $FT" >&2
        exit 1
      fi
      ;;
  esac
fi

cp "$SRC_FFMPEG" "$FFMPEG"
cp "$SRC_FFPROBE" "$FFPROBE"
chmod +x "$FFMPEG" "$FFPROBE"

# Gatekeeper quarantine breaks unsigned helper launches on fresh downloads.
if [[ "$(uname -s)" == "Darwin" ]] && command -v xattr >/dev/null 2>&1; then
  xattr -dr com.apple.quarantine "$FFMPEG" "$FFPROBE" 2>/dev/null || true
fi

echo ""
echo "ffmpeg ready in bin/ffmpeg/ (arch=$ARCH)"
if [[ "$(uname -s)" == "Darwin" ]]; then
  "$FFMPEG" -version | head -n 1
  "$FFPROBE" -version | head -n 1
  if "$FFMPEG" -hide_banner -encoders 2>/dev/null | grep -q h264_videotoolbox; then
    echo "VideoToolbox: h264_videotoolbox available"
  else
    echo "NOTE: h264_videotoolbox not listed — encode will fall back to libx264"
  fi
else
  echo "(skipping -version on non-Darwin host; Mach-O arch check passed)"
  command -v file >/dev/null 2>&1 && file "$FFMPEG" "$FFPROBE"
fi
