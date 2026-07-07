# Plan

Master TODO consolidation and coverage truth — completed 2026-07-07.

1. ✅ **Audit plan docs** — Extracted orphaned todos from BETA_GO_LIVE, BETA_TESTER_PLAN, GAP_ANALYSIS, CREATOR_PLATFORM, TECHNICAL_DESIGN, BETA_KNOWN_ISSUES; mapped to MASTER sections.
2. ✅ **Coverage Truth (§3.10)** — Added canonical command, 110% definition, scope/exclusions, phase waivers, footguns to `docs/MASTER_TODO.md`.
3. ✅ **Consolidate MASTER** — Expanded §8 (8.9–8.19), §3.11 CI job; resolved §6.5/§6.7 conflict; updated §3.5/§3.7 with current module gaps.
4. ✅ **Enforce coverage** — `scripts/verify_coverage.ps1`, `verify_stack.ps1 -WithCoverage`, `.github/workflows/test.yml`.
   - Output: `scripts/verify_coverage.ps1`
   - Output: `scripts/verify_stack.ps1` (`-WithCoverage`)
   - Output: `.github/workflows/test.yml`
5. ✅ **Sync downstream docs** — BETA_GO_LIVE, BETA_TESTER_PLAN, GAP_ANALYSIS (rev 7), TECHNICAL_DESIGN §11, BETA_KNOWN_ISSUES, CONTRIBUTING, CREATOR_PLATFORM.
6. ✅ **PLAN.md** — This file.

**Refresh coverage %:** when Docker is up, run `.\scripts\verify_coverage.ps1` — Phase 0 invites stay blocked until it passes (≥95% line).
