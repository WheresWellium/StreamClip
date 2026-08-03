# Stale-folder audit (post beta.23 / beta.24)

**Date:** 2026-08-03  
**Method:** git last-touch per path (not filesystem mtime — checkout resets those).  
**Cutoff:** paths with no commit since **2026-08-01** (~2+ days before audit).  
**Product truth:** qClip desktop **`1.0.0-beta.24`**; Docker = dev + future Pro SKU.

## Verdict

**No top-level product folder is safe to delete.** Stale *dates* mostly mean “stable infrastructure,” not “orphaned.” The real debt is **narrative/version drift** in older docs and one **desktop packaging gap** (`assets/` not in the sidecar bundle).

## Top-level paths (pre–Aug 1)

| Path | Last touch | Classification | Why |
|------|------------|----------------|-----|
| `assets/` | 2026-06-29 | **KEEP** + package into desktop | Overlay vault (GIF/SFX/stickers). Used by `core/overlay.py`, compose mounts, Dockerfile. **Gap:** not in `packaging/pyinstaller/streamclip-sidecar.spec` `datas`. |
| `bin/` | 2026-07-07 | **KEEP** | Placeholder + README; ffmpeg binaries gitignored, downloaded at build. Required by desktop packaging. |
| `alembic/` | 2026-07-28 | **KEEP** | Live migrations; sidecar boots `upgrade head`. Head is `0014_sqlite_timestamp_defaults` (no `0013` file). |
| `deploy/` | 2026-07-28 | **KEEP** + **UPDATE** | Only `PRODUCTION.md` (no Caddyfile). Still the Pro/self-host runbook; skills overstate contents. |
| `.cursor/` | 2026-07-30 | **KEEP** + **UPDATE** | Agent rules/skills. Some skills still Docker-first vs desktop-primary. |
| `pipeline.py` | 2026-07-07 | **KEEP** (dev CLI) | Documented in README; not on desktop hot path. Soft-delete only if CLI is dropped. |
| `PLAN.md` | 2026-07-28 | **UPDATE** | Still frames Phase 0 Docker as “current focus”; contradicts beta.24 desktop ship. |
| `COMMERCIAL.md` | 2026-07-28 | **KEEP** + **UPDATE** | License terms still needed; brand/Pro narrative is Docker-era. |
| `openapi.json` | 2026-07-07 | **UPDATE** | Behind live routes (license activations, support feedback, health/models, etc.). Regen via CONTRIBUTING. |
| `Dockerfile` / `docker-compose*.yml` | Jul 9–28 | **KEEP** | Dev stack + future Pro. Not creator product. |
| `requirements*.txt` | 2026-07-07 | **KEEP** | Still wired into Docker, CI, sidecar builds. |

## Touched recently (not stale — confirmed still needed)

| Path | Role |
|------|------|
| `apps/`, `backend/`, `web/`, `tests/`, `scripts/`, `docs/` | Actively shipping beta.24 |
| `api/` | Henna serverless F13 support ingest — **not** a duplicate of `backend/api/` |
| `packaging/`, `config/`, `static/`, `desktop_sidecar/` | Desktop product path |

## Nested modules idle >2 days (still needed)

| Path | Last touch | Note |
|------|------------|------|
| `core/commerce/` | 2026-07-17 | Lemon Squeezy / license activate — live |
| `core/distribution/` | 2026-07-24 | Social publish — live |
| `core/support/` | 2026-07-24 | Support pack — live (F13 now also hits henna GitHub Issues) |
| `core/vault/` | 2026-07-24 | Asset vault — live |
| `docs/commercial/`, `docs/superpowers/`, `docs/design/`, `docs/share/` | Jul 28–30 | Archive / outreach; keep |
| `web/hooks/`, `web/public/` | Jul 7–28 | Web app pieces; keep |

## Doc / version drift (customer or operator facing)

| Doc | Issue | Action in this PR |
|-----|--------|-------------------|
| `docs/tutorials/TUTORIAL_INSTALL.md` | Cited beta.6 | Bump to beta.24 |
| `docs/tutorials/TUTORIAL_TROUBLESHOOTING.md` | “Install beta.8” | Point at Latest |
| `docs/BETA_GO_LIVE.md` | Download beta.8 | Point at Latest / beta.24 |
| `docs/DESKTOP_SIGNING.md` | Latest target beta.22 | beta.24 |
| `docs/DESKTOP_UPGRADE_MATRIX.md` | Matrix ends at beta.7 | Extend support window → beta.24 |
| `PLAN.md` | Docker Phase 0 as current focus | Truth banner → SESSION_STATE / desktop |
| Historical evidence / known-issues “fixed in beta.N” | OK as history | Leave |

## Do not delete

- Docker / alembic / bin / assets / requirements / compose  
- `api/` (henna) vs `backend/api/` (FastAPI) — different roles  
- `apps/desktop/assets/` vs root `assets/` — icons vs overlays  

## Follow-ups (not done here)

1. Regenerate `openapi.json` + `web/lib/api/openapi.ts` from running FastAPI.  
2. Refresh `COMMERCIAL.md` / `deploy/PRODUCTION.md` brand + desktop-primary framing.  
3. Align `.cursor/skills/streamclip-technical-design` to desktop-primary TDD Rev 5.  
4. Broader `PLAN.md` / `MASTER_TODO.md` phase rename (desktop = active product track).
