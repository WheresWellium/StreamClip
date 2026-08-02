# Internal documentation (not published on henna)

These files live in `docs/` for version control and agents but are **excluded from the public MkDocs site** (`exclude_docs` in `mkdocs.yml`). They are not in customer navigation and are not deployed to Vercel.

## Customer henna (published)

| Nav | File | Role |
|-----|------|------|
| Home | `index.md` | **Only public page** — download buttons + install / activate / use steps |

Old customer pages (`BETA_DOWNLOAD`, quickstart, FAQ, known issues, tutorials) stay in the repo for operators but are **not published**. `vercel.json` redirects those URLs to `/` (or `/#download` / `/#use`).

**In-app Help:** `web/app/help/page.tsx` embeds henna (`HELP_TOPICS` + `helpHref` in `web/lib/docs.ts`). Legacy paths remap in `LEGACY_HELP_DOCS_PATHS` (keep aligned with `vercel.json`).

## Excluded — operators / engineering

| File | Purpose |
|------|---------|
| `BETA_DOWNLOAD.md`, `BETA_TESTER_QUICKSTART.md`, `BETA_FAQ.md`, `BETA_KNOWN_ISSUES.md`, `tutorials/` | Former customer pages — operators only |
| `GAP_ANALYSIS.md`, `MASTER_TODO.md`, `SESSION_STATE.md` | Planning registers |
| `BETA_GO_LIVE.md`, `BETA_OPS_PHASE0.md`, `BETA_ON_CALL.md`, `BETA_INVITE_PACK.md` | Cohort ops |
| `BETA_TESTER_PLAN.md`, `BETA_COHORT_EXIT.md` | Acceptance / exit evidence |
| `MACOS_INSTALLER.md`, `DESKTOP_SIGNING.md`, `CLEAN_DESKTOP_VM_VERIFY.md`, `DESKTOP_*` | Builder / signing / desktop ship-gate runbooks |
| `OPS_ALERTING.md`, `BETA_OBSERVABILITY.md`, `distribution-runbook.md` | Ops |
| `PERFORMANCE.md`, `TECHNICAL_DESIGN.md`, `ADR-*`, `CREATOR_PLATFORM.md` | Architecture |
| `commercial/`, `evidence/`, `superpowers/`, `design/`, `share/` | Internal research / specs |
| `FIGMA_LINKS.md` (root stub) → `THEME_SKINS.md` + `design/FIGMA_LINKS.md` | Figma registers (do not publish) |

**Coverage gate:** `scripts/verify_coverage.ps1` (rules in `MASTER_TODO.md` §3.10).

**Verify exclusion:**

```bash
python -m mkdocs build --strict
# site/ should contain index.html only (plus Material assets) — no BETA_*, tutorials, gap_analysis, etc.
```

**Production URL:** https://streamclip-henna.vercel.app/  
Do **not** use `streamclip.vercel.app` (bound to an unrelated old project).
