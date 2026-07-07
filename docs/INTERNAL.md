# Internal documentation (not published)

These files live in `docs/` for version control and agent workflows but are **excluded from the public MkDocs site** (`exclude_docs` in `mkdocs.yml`). They are not linked in navigation and are not deployed to Vercel or GitHub Pages.

| File | Purpose | Update when |
|------|---------|-------------|
| [GAP_ANALYSIS.md](GAP_ANALYSIS.md) | Doc vs code / UX gap register | After gap-analysis runs, releases, major refactors |
| [MASTER_TODO.md](MASTER_TODO.md) | Engineering backlog and ship checklist | When closing or opening beta blockers |
| [BETA_KNOWN_ISSUES.md](BETA_KNOWN_ISSUES.md) | Beta tester limitations and SLAs | Each beta wave |

**Workflow:** run the `streamclip-gap-analysis` skill (`.cursor/skills/streamclip-gap-analysis/SKILL.md`) — it updates `GAP_ANALYSIS.md` in place. Sync `MASTER_TODO.md` when items move to done or new gates appear.

**Verify exclusion before sharing a docs URL:**

```bash
python -m mkdocs build --strict
# Confirm site/ contains no gap_analysis or master_todo HTML
```

Public site deploy: **Vercel** (`vercel.json` at repo root).
