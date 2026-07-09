# Internal documentation (not published)

These files live in `docs/` for version control and agent workflows but are **excluded from the public MkDocs site** (`exclude_docs` in `mkdocs.yml`). They are not linked in navigation and are not deployed to Vercel or GitHub Pages.

| File | Purpose | Update when |
|------|---------|-------------|
| [GAP_ANALYSIS.md](GAP_ANALYSIS.md) | Doc vs code / UX gap register | After gap-analysis runs, releases, major refactors |
| [MASTER_TODO.md](MASTER_TODO.md) | Engineering backlog and ship checklist | When closing or opening beta blockers |
| [PLAN.md](../PLAN.md) | Short-lived execution tracker (repo root) | During multi-step agent plans |
| [BETA_KNOWN_ISSUES.md](BETA_KNOWN_ISSUES.md) | Beta tester limitations and SLAs | Each beta wave |
| [OPS_ALERTING.md](OPS_ALERTING.md) | Autonomous ops webhook + Sentry (no n8n) | When `OPS_WEBHOOK_URL` or Sentry DSN changes |
| [BETA_OPS_PHASE0.md](BETA_OPS_PHASE0.md) | Phase 0 keys, support triage, invite template | Each beta wave |
| [BETA_INVITE_PACK.md](BETA_INVITE_PACK.md) | Pre-invite checklist, fresh-reader §8.14, send steps §8.15 | Before each cohort wave |

**Coverage gate:** canonical rules in [MASTER_TODO.md §3.10](MASTER_TODO.md); run `scripts/verify_coverage.ps1`.

**Workflow:** run the `streamclip-gap-analysis` skill (`.cursor/skills/streamclip-gap-analysis/SKILL.md`) — it updates `GAP_ANALYSIS.md` in place. Sync `MASTER_TODO.md` when items move to done or new gates appear.

**Verify exclusion before sharing a docs URL:**

```bash
python -m mkdocs build --strict
# Confirm site/ contains no gap_analysis or master_todo HTML
```

Public site deploy: **Vercel** (`vercel.json` at repo root).

**Production URL:** https://streamclip-henna.vercel.app/ (team **wellium**, project `streamclip`).

**Do not use** `streamclip.vercel.app` — that alias is bound to an old unrelated deployment (blank French landing page). To reclaim it: remove the alias on the other Vercel project, then `npx vercel alias <deployment-url> streamclip.vercel.app` from this repo.
