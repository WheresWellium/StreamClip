# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-07 (95.40% line + distribution UX polish + hot-path tests)

## Current focus

**Line gate 95.40%** GREEN. Distribution UX: stale-state refetch, deep links, batch-publish guard. Hot-path tests + branch measure script. Phase 0 blocker: clean-VM verify (`docs/CLEAN_VM_VERIFY.md`).

## Blockers

- §3.8 clean-VM `verify_stack.ps1` — cannot run from dev machine; runbook at `docs/CLEAN_VM_VERIFY.md`
- Full 110% (100% line + branch ≥85% + full OAuth E2E) is Phase 1+

## Next steps (ordered)

1. User: clean-VM verify per `docs/CLEAN_VM_VERIFY.md`
2. Phase 1: ratchet line 95→100 (404 stmts); enable branch gate `-FailUnderBranch 85`
3. Commit when user asks

## Key paths

- Coverage: `scripts/verify_coverage.ps1`, `scripts/verify_branch_coverage.ps1`
- Tests: `tests/test_coverage_hotpath_finish.py`, `tests/test_coverage_tier_b_api.py`
- E2E: `web/e2e/happy-path.spec.ts`
- Truth: `docs/MASTER_TODO.md` §3.10
