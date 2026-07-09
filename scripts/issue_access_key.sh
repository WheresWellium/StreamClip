#!/usr/bin/env bash
# Issue a StreamClip license key via Docker API container.
#
# Usage:
#   ./scripts/issue_access_key.sh
#   ./scripts/issue_access_key.sh --email matt@maius.com
#   ./scripts/issue_access_key.sh --tier admin --email matt@maius.com
#   ./scripts/issue_access_key.sh --list --limit 30

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

LOCAL="$REPO_ROOT/scripts/issue_access_key.py"
if [[ ! -f "$LOCAL" ]]; then
  echo "Missing $LOCAL" >&2
  exit 1
fi

docker compose up -d api
docker compose cp "$LOCAL" api:/app/scripts/issue_access_key.py
docker compose exec -e PYTHONPATH=/app api python scripts/issue_access_key.py "$@"
