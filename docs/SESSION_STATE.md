# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-18

## Active chats

None.

## Current focus

Ship **M4 feedback ops**, **M5 account UI**, **P2 quality**, and **external product UI hardening** on `master`. Theme-skins worktree (`feat/theme-skins`) should be rebased/merged after master lands.

## Blockers

- Vercel docs redeploy pending (mkdocs nav trim + beta tutorial copy).
- Phase 0 exit (T0 cohort) and EV signing (§4.10) unchanged.

## Validation

- Run `npm run typecheck` in `web/` after merge.
- Run `scripts/verify_coverage.ps1` + `scripts/verify_stack.ps1` before beta promotion.

## Next steps

1. Commit master (M4/M5/P2 + external UI + docs).
2. `mkdocs build --strict` + Vercel deploy docs site.
3. Rebase `feat/theme-skins` onto master; resolve theme-only deltas.
4. Desktop installer publish when web changes ship.

## Key paths

- `web/lib/dev-tools.ts` — `NEXT_PUBLIC_DEV_TOOLS` product gate
- `web/app/settings/page.tsx` — M5 sections + external gating
- `core/support/` — M4 ticket lifecycle
- `docs/BETA_TESTER_QUICKSTART.md` — app-first Ready check copy
