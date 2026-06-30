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

## Debugging Next.js (server-side)

Official guide: [Next.js — Debugging server-side code](https://nextjs.org/docs/app/guides/debugging#server-side-code)

### VS Code / Cursor

1. Stop the Docker `web` service if it owns port 3000: `docker compose stop web`
2. Open **Run and Debug** (`Ctrl+Shift+D`) and start **StreamClip: debug server-side**
3. Set breakpoints in Server Components, Server Actions (`web/app/actions/`), and route handlers

Configs live in `.vscode/launch.json` at the repo root (`cwd` is `web/`).

### Chrome DevTools (Node inspector)

```bash
cd web && npm run dev:inspect
```

Open `chrome://inspect` and attach to the Node process. Source paths appear as `webpack://streamclip-web/./…` per the Next.js docs.

For `--inspect-brk` / `--inspect-wait`, use `NODE_OPTIONS` instead of `--inspect` (see the linked guide).

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
