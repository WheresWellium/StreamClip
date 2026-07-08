# Jet Stream documentation

**Jet Stream** *(internal name: StreamClip)* turns long-form video into viral vertical shorts — install the [Windows app](BETA_DOWNLOAD.md) or self-host with Docker.

This site is built from the markdown in `docs/` in the repository. For interactive API reference, run the stack and open [Swagger UI](http://localhost:8000/docs) (also proxied at `/docs` on the web app in dev).

!!! tip "Creators"
    [**Download StreamClip for Windows**](BETA_DOWNLOAD.md) — no Docker, no Git, one-click installer.

## Start here

| Audience | Document |
|----------|----------|
| **Creators (Windows)** | [**Download installer**](BETA_DOWNLOAD.md) — one-click setup, no Docker |
| Beta testers (Docker) | [15-minute quickstart](BETA_TESTER_QUICKSTART.md) → [full test plan](BETA_TESTER_PLAN.md) |
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
