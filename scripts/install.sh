#!/usr/bin/env bash
# qClip production installer — Docker prereq checks, health validation, compose up
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> qClip install"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker is required. Install Docker Desktop or docker-ce first."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: docker compose plugin is required."
  exit 1
fi

ENV_FILE="${ENV_FILE:-.env.production}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f .env.production.example ]]; then
    echo "==> Creating $ENV_FILE from .env.production.example"
    cp .env.production.example "$ENV_FILE"
    echo "    Edit $ENV_FILE with your secrets, then re-run this script."
    exit 0
  fi
  echo "ERROR: Missing $ENV_FILE"
  exit 1
fi

echo "==> Pulling images"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull

echo "==> Starting stack"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

echo "==> Waiting for API health"
for i in $(seq 1 30); do
  if curl -sf "http://localhost:${API_PORT:-8000}/api/health" >/dev/null 2>&1; then
    echo "    API healthy"
    break
  fi
  sleep 2
  if [[ "$i" -eq 30 ]]; then
    echo "WARN: API health check timed out — check logs: docker compose -f $COMPOSE_FILE logs api"
    exit 1
  fi
done

WEB_PORT="${WEB_PORT:-3000}"
echo ""
echo "qClip is running:"
echo "  Web UI:  http://localhost:${WEB_PORT}"
echo "  API:     http://localhost:${API_PORT:-8000}/docs"
echo ""
echo "Complete onboarding at http://localhost:${WEB_PORT}/onboarding"
