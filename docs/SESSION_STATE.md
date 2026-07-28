# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-28 (T66 mock UI e2e green; Phase 0 agent gaps closed)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `cursor/phase0-exit-and-beta-hardening` | Phase 0 / T66 closeout | — | e2e + ops/SMTP already landed |

## Current focus

Agent-owned UX/reliability + **T66 UI journey e2e** are done. Mock-API Playwright suite **23/23 PASS** (`npm run test:e2e:ui-journey`). Remaining work is human ops/hardware.

## Blockers (human-only — cannot automate)

- O12 — merge/publish desktop → `1.0.0-beta.5` when ready.
- O6 — send invite pack.
- ~~O7~~ ✅ SMTP-only alerting verified live.
- O5 — fill on-call `<…_NAME>` tokens.
- O4 — run `capture_phase0_evidence.ps1` during live cohort windows.
- O11 — buy EV / Azure Trusted Signing.
- O14 — Mac host builds live `.dmg`.
- ~~T66~~ ✅ mock UI journey (create→review→publish + failure + onboarding).
- GPU hardware smoke (NVENC/CUDA) — needs GPU box.

## Validation

- Licensing blocklist ✅ · SMTP alerting live PASS · ops delivery fallback ✅
- **UI e2e 23/23** — journey + failure-paths + onboarding (`web/e2e/`, `test:e2e:ui-journey`)
- Note: Docker web `.next` anonymous volume can go stale vs source — wipe `/app/.next/*` + restart web if brand/UI drifts

## Next steps

1. User: review/merge branch; O12 publish; O5/O6 ops.
2. Optional: GPU smoke when hardware available; re-run `verify_coverage.ps1` after backend commit.

## Key paths

- E2E: `web/e2e/journey-create-review.spec.ts`, `failure-paths.spec.ts`, `onboarding-first-run.spec.ts`, `support/mock-api.ts`
- Gaps: `docs/GAP_ANALYSIS.md` · Exit: `docs/BETA_COHORT_EXIT.md`
