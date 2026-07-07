# Jet Stream documentation

**Jet Stream** *(internal name: StreamClip)* is a self-hosted AI clip pipeline: from a long-form VOD to vertical, captioned clips ready to publish — without subscription tokens or watermarks.

This site is built from the markdown in `docs/` in the repository. For interactive API reference, run the stack and open [Swagger UI](http://localhost:8000/docs) (also proxied at `/docs` on the web app in dev).

## Start here

| Audience | Document |
|----------|----------|
| Beta testers | [15-minute quickstart](BETA_TESTER_QUICKSTART.md) → [full test plan](BETA_TESTER_PLAN.md) |
| Operators | [Distribution runbook](distribution-runbook.md) · [Performance budgets](PERFORMANCE.md) |
| Engineers | [Technical design](TECHNICAL_DESIGN.md) · [Creator platform map](CREATOR_PLATFORM.md) |
| Launch gate | [Beta go-live checklist](BETA_GO_LIVE.md) |

## Local preview

```bash
pip install -r docs/requirements.txt
python -m mkdocs serve -a 127.0.0.1:8001
```

Open http://127.0.0.1:8001 (MkDocs dev server — not the FastAPI port on 8000).

## Build (strict)

```bash
mkdocs build --strict
```

Output lands in `site/` (gitignored).
