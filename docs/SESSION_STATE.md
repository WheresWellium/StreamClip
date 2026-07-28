# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-28 (Phase 0 exit tooling + beat healthcheck + migration verified)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| — | — | — | Locks empty |

## Current focus

Coverage **PASS 96%**. Alembic **0012 head applied** (seats table + 1-row backfill). Beat **healthy** (compose healthcheck override — was false-unhealthy from inherited API curl). Phase 0 exit **tooling complete** — residual steps are human-only (names, cert purchase, Mac host, invite send, real OPS webhook).

## Blockers (human-only)

- O12 — user commit loader + publish → `1.0.0-beta.5`.
- O6 send — operator spot-check + manual send (`BETA_INVITE_PACK.md` §5).
- O7 — paste real `OPS_WEBHOOK_URL` locally (mock verify already PASS).
- O5 — fill `<…_NAME>` tokens in `BETA_ON_CALL.md` (~2 min).
- O4 — run `capture_phase0_evidence.ps1` at T0…H72 during live cohort.
- O11 — buy EV / Azure Trusted Signing (`DESKTOP_SIGNING.md` Paths C/D).
- O14 — borrowed Mac builds live `.dmg` (`MACOS_INSTALLER.md` 30-min).

## Validation

- Coverage ✅ 96% · Health ✅ 9/9 · beat ✅ healthy · alembic ✅ `0012` head
- Web typecheck/lint ✅ · unit 19/19 · ops webhook mock ✅ · seats migration ✅
- Evidence script ✅ (`docs/evidence/` SAMPLE) · signing preflight ✅ unsigned path
- Loader e2e ✅ · O9 seat UX ✅ · O8 AUTH guard ✅ · jti claim on entitlement JWT ✅

## Next steps

1. **User:** fill on-call names; O12 commit+publish beta.5; O6 send; O7 webhook URL.
2. **Cohort:** capture T0 at invite; H2/H24/H72 via evidence script → fill exit pack.
3. **Trust:** EV/Azure cert when ready; Mac DMG when host available.

## Key paths

- Exit: `docs/BETA_COHORT_EXIT.md` · `scripts/capture_phase0_evidence.ps1` · `docs/evidence/`
- Signing: `docs/DESKTOP_SIGNING.md` · macOS: `docs/MACOS_INSTALLER.md`
- Gaps: `docs/GAP_ANALYSIS.md` · O12: `tmp/o12-loader-republish.md`
- Commercial (board): `docs/commercial/` (inventory, competitive analysis, pricing assessment; scratch `tmp/competitor-*.md`)
