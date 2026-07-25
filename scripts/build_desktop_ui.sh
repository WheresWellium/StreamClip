#!/usr/bin/env bash
# Build static Next.js UI for desktop sidecar (ADR-001 §4.7).
# Darwin/Linux equivalent of scripts/build_desktop_ui.ps1.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

UI_OUT="$ROOT/static/ui"
WEB_DIR="$ROOT/web"
MIDDLEWARE="$WEB_DIR/middleware.ts"
MIDDLEWARE_DEV="$WEB_DIR/middleware.dev.ts"
API_DIR="$WEB_DIR/app/api"
API_STASH="$WEB_DIR/app/_api.desktop-stash"

middleware_moved=0
api_moved=0

cleanup() {
  if [[ "$api_moved" -eq 1 && -d "$API_STASH" ]]; then
    rm -rf "$API_DIR"
    mv "$API_STASH" "$API_DIR"
  fi
  if [[ "$middleware_moved" -eq 1 && -f "$MIDDLEWARE_DEV" ]]; then
    mv "$MIDDLEWARE_DEV" "$MIDDLEWARE"
  fi
}
trap cleanup EXIT

echo "Building static UI (NEXT_STATIC_EXPORT=1)..."
cd "$WEB_DIR"
export NEXT_STATIC_EXPORT=1
export NEXT_PUBLIC_DEV_TOOLS=0
export NEXT_PRIVATE_WORKER_THREADS=false

if [[ -f "$MIDDLEWARE" ]]; then
  rm -f "$MIDDLEWARE_DEV"
  mv "$MIDDLEWARE" "$MIDDLEWARE_DEV"
  middleware_moved=1
fi

if [[ -d "$API_DIR" ]]; then
  rm -rf "$API_STASH"
  mv "$API_DIR" "$API_STASH"
  api_moved=1
fi

npm run build

EXPORT_DIR="$WEB_DIR/out"
if [[ ! -d "$EXPORT_DIR" ]]; then
  echo "ERROR: web/out not found after build" >&2
  exit 1
fi

echo "Copying web/out -> static/ui ..."
rm -rf "$UI_OUT"
mkdir -p "$UI_OUT"
cp -R "$EXPORT_DIR"/. "$UI_OUT"/

echo "Static UI ready at static/ui/"
