# Clean-VM stack verification (MASTER_TODO §3.8)

**Purpose:** Phase 0 beta invite gate. Proves StreamClip installs and verifies on a **fresh Windows 11 VM**, not a long-lived dev machine.

## Prerequisites

- Windows 11 VM (clean snapshot: no prior StreamClip clone, no Docker layers from dev)
- Git, Docker Desktop (WSL2 backend), PowerShell 7+
- Network access to pull images / GHCR if using prod compose

## Steps

1. Clone the repo at the commit/tag you intend to ship.
2. Copy `.env.example` → `.env` and set required secrets (see `README.md`).
3. From repo root:

```powershell
docker compose up --build -d
docker compose exec -T api alembic upgrade head
.\scripts\verify_stack.ps1
.\scripts\verify_coverage.ps1
```

4. Optional E2E (stack must include `web` on port 3000):

```powershell
cd web
npm ci
npx playwright install chromium
cd ..
.\scripts\verify_stack.ps1 -RunE2E
```

5. Record in release notes:
   - VM image / snapshot name
   - Commit SHA
   - `verify_coverage.ps1` total % line
   - `verify_stack.ps1` pass/fail
   - Date (UTC)

## Pass criteria

| Check | Command | Required |
|-------|---------|----------|
| Stack health | `verify_stack.ps1` | Yes |
| Line coverage ≥95% | `verify_coverage.ps1` | Yes |
| E2E smoke | `verify_stack.ps1 -RunE2E` | Phase 1+ (optional Phase 0) |
| Branch hot paths ≥85% | `verify_branch_coverage.ps1 -FailUnderBranch 85` | Phase 1+ |

## Known dev-machine false positives

- Reusing Docker volumes from prior runs
- Leftover `.env` with dev-only keys
- `verify_stack.ps1 -WithCoverage` on dev may diverge slightly from `verify_coverage.ps1` — **canonical gate is `verify_coverage.ps1`**

## Sign-off template

```
Clean-VM verify (§3.8)
VM: Windows 11 __________  Snapshot: __________
Commit: __________
verify_stack.ps1: PASS / FAIL
verify_coverage.ps1: ___% PASS / FAIL
Tester: __________  Date: __________
```

## Latest recorded sign-off (2026-07-09)

```
Clean-VM verify (§3.8) — clean-slate Docker proxy (Hyper-V unavailable)
Host: operator Windows 11 + Docker Desktop WSL2
Method: docker compose down -v → up --build -d → alembic upgrade head
Commit: 6ca96b94284a4c98d9254dea98526fcfdd18041d (+ local gate fixes)
verify_stack.ps1: PASS
verify_coverage.ps1: 95.02% PASS
verify_branch_coverage.ps1 -FailUnderBranch 85: PASS
Tester: agent  Date: 2026-07-09
Evidence: tmp/verify_stack_clean.txt, tmp/clean_verify_log.txt, docs/BETA_GO_LIVE.md §8
```
