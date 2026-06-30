# StreamClip — Contributing

## Development setup

```bash
docker compose up --build -d
docker compose exec api alembic upgrade head
```

Frontend (with bind-mounted `./web`):

```bash
cd web && npm install && npm run dev
```

## Type generation (OpenAPI)

Regenerate frontend types after API schema changes:

```bash
curl -s http://localhost:8000/openapi.json -o openapi.json
cd web && npx openapi-typescript ../openapi.json -o lib/api/openapi.ts
npm run typecheck
```

Hand-written types in `web/lib/api/types.ts` should be replaced with imports from `openapi.ts` when fields change.

## Tests

```bash
# API unit tests (host or container)
pip install pytest pytest-asyncio pytest-cov httpx
pytest

# End-to-end smoke (requires running stack + test video in workspace/)
docker compose exec api python /app/workspace/smoke_test.py

# Playwright (requires web + api running)
cd web && npx playwright test
```

## Commits

Use conventional commits per phase: `feat(phase-N): …`, `docs(phase-N): …`.
