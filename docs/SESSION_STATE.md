# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-18

## Active chats

None.

## Current focus

`master` @ `34d6fd2` + follow-up: beta feedback area routing, MASTER_TODO §6.14. `feat/theme-skins` merged with master @ `3bffbbe` — open PR for theme system + ship hardening.

## Blockers

- Phase 0 exit (T0 cohort) and EV signing (§4.10) unchanged.

## Validation

- `npm run typecheck` in `web/` on master and theme-skins
- `scripts/verify_coverage.ps1` + `scripts/verify_stack.ps1` before beta promotion

## Next steps

1. Push `master` and `feat/theme-skins`; open theme-skins PR.
2. Desktop installer publish after web changes ship to master.
3. M4 admin ticket UI (optional).

## Key paths

- `web/lib/dev-tools.ts` — external product gate
- `web/lib/themes.ts` + `globals.css` — theme system (theme-skins branch)
- `web/components/support/beta-feedback-dialog.tsx` — area + topic routing
- `core/support/` — M4 ticket lifecycle
