#!/usr/bin/env bash
# Issue a ready-to-paste ADMIN license key for local testing (macOS / Linux).
#
# Usage (repo root, stack running via `docker compose up -d`):
#   ./scripts/dev_admin_key.sh
#   ./scripts/dev_admin_key.sh you@example.com
#
# Prints a SCPRO-XXXX-XXXX-XXXX-XXXX admin key registered in your local DB.
# Paste it in the web UI: Settings -> License -> Activate.
set -euo pipefail

EMAIL="${1:-dev@streamclip.local}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is required and the stack must be running (docker compose up -d)." >&2
    exit 1
fi

echo "==> Issuing admin license key for ${EMAIL} ..."

# issue_beta_keys.py prints CSV: email,license_key,order_id,tier
csv="$(docker compose exec -T -e PYTHONPATH=/app api \
    python scripts/issue_beta_keys.py --emails "${EMAIL}" --tier admin)" || {
    echo "Key issuance failed. Is the stack up? Try: docker compose up -d" >&2
    exit 1
}

key="$(printf '%s\n' "$csv" | awk -F, -v e="$EMAIL" '$1==e {print $2; exit}')"
if [ -z "${key:-}" ]; then
    printf '%s\n' "$csv"
    echo "Could not parse the license key from output above." >&2
    exit 1
fi

echo ""
echo "Admin license key (tier=admin, full access):"
echo "  ${key}"
echo ""
echo "Activate it: open http://localhost:3000 -> Settings -> License -> paste -> Activate."
