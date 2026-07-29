# Internal documentation (not published on henna)

These files live in `docs/` for version control and agents but are **excluded from the public MkDocs site** (`exclude_docs` in `mkdocs.yml`). They are not in customer navigation and are not deployed to Vercel.

## Customer henna (published)

| Nav | File | Role |
|-----|------|------|
| Home | `index.md` | One CTA → Install |
| Install | `BETA_DOWNLOAD.md` | Windows `.exe` + Mac Docker |
| First clip | `BETA_TESTER_QUICKSTART.md` | Job → approve → publish |
| Help | `BETA_FAQ.md`, `BETA_KNOWN_ISSUES.md`, `tutorials/TUTORIAL_TROUBLESHOOTING.md` | Answers / limits / fixes |

## Excluded — operators / engineering

| File | Purpose |
|------|---------|
| `GAP_ANALYSIS.md`, `MASTER_TODO.md`, `SESSION_STATE.md` | Planning registers |
| `BETA_GO_LIVE.md`, `BETA_OPS_PHASE0.md`, `BETA_ON_CALL.md`, `BETA_INVITE_PACK.md` | Cohort ops |
| `BETA_TESTER_PLAN.md`, `BETA_COHORT_EXIT.md` | Acceptance / exit evidence |
| `MACOS_INSTALLER.md`, `DESKTOP_SIGNING.md` | Builder / signing runbooks |
| `OPS_ALERTING.md`, `BETA_OBSERVABILITY.md`, `distribution-runbook.md` | Ops |
| `PERFORMANCE.md`, `TECHNICAL_DESIGN.md`, `ADR-*`, `CREATOR_PLATFORM.md` | Architecture |
| `commercial/`, `evidence/`, `superpowers/`, `design/` | Internal research / specs |
| Extra tutorials (`TUTORIAL_INSTALL`, GPU, vault, YouTube, …) | Deep dives — content kept in repo; not on henna nav |

**Coverage gate:** `scripts/verify_coverage.ps1` (rules in `MASTER_TODO.md` §3.10).

**Verify exclusion:**

```bash
python -m mkdocs build --strict
# site/ should not contain gap_analysis, master_todo, macos_installer, etc.
```

**Production URL:** https://streamclip-henna.vercel.app/  
Do **not** use `streamclip.vercel.app` (bound to an unrelated old project).
