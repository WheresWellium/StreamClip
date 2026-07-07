# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-07 (coverage gate cleared + continual-learning hook + disk-space incident)

## Current focus

**§3.5 coverage gate is GREEN (95.01%)** — reproduced fresh this session via `verify_coverage.ps1` (matches prior session's measurement; docs already synced). `verify_stack.ps1` (no args) also passes, including `web` container health. Remaining Phase 0 blocker is **§3.8: clean-VM `verify_stack.ps1`** run (this dev machine doesn't count).

## Context compaction + continual learning (2026-07-07)

| Artifact | Role |
|----------|------|
| `docs/SESSION_STATE.md` | Rolling execution state — read first after summarization |
| `AGENTS.md` | Durable preferences/facts (≤12 bullets/section) |
| `.cursor/rules/conversation-compaction.mdc` | Agent discipline (subagents, no output paste) |
| `.cursor/hooks/pre-compact.ps1` | Flush SESSION_STATE before Cursor compacts |
| `.cursor/hooks/stop-compaction.ps1` | Refresh SESSION_STATE every 6 turns / 45 min |
| `.cursor/hooks/continual-learning-stop.ps1` | PowerShell port of `continual-learning` plugin's stop hook (bun unavailable); mines `agent-transcripts` into `AGENTS.md` via `agents-memory-updater` subagent. Trial cadence: 3 turns/15min for 24h, then 10 turns/120min. State: `.cursor/hooks/state/continual-learning.json` + `-index.json`. |

## Active goal

§3.8 clean-VM `verify_stack.ps1` run is now the sole Phase 0 invite blocker. After that: 110% plan (§3.7 branch hot-paths, §3.3 Playwright) for Phase 1.

## Blockers

- **Disk space (ongoing, watch closely):** C: drive was at ~1GB free (2026-07-07); freed to ~6GB via Recycle Bin empty + Temp clear (both non-admin-safe). `C:\$Recycle.Bin` still shows 35GB used but couldn't be cleared without admin rights (likely orphaned other-user-profile data) — user declined further action beyond the safe cleanup. Docker image builds are disk-hungry (saw context transfers balloon past 2GB); re-check free space before any full rebuild.
- §3.8 clean-VM `verify_stack.ps1` not yet run (needs an actual clean Windows 11 VM, not this dev box).
- Many consolidation + ratchet changes still uncommitted (user has not requested commit).

## Decisions (durable)

| Topic | Decision |
|-------|----------|
| Coverage command | `docker compose exec -T api pytest tests/ -m "not desktop" -q --cov=backend --cov=core --cov-report=term-missing:skip-covered` or `.\scripts\verify_coverage.ps1` |
| Phase 0 language | §3.5 now GREEN; blocker language should cite **§3.8 clean-VM verify** only, not coverage |
| Docker + PowerShell | Never wrap `verify_coverage.ps1`/`verify_stack.ps1` with `2>&1 \| Tee-Object` — `$ErrorActionPreference='Stop'` + stderr redirection throws a spurious `NativeCommandError` on normal `docker compose build` progress output even on success |
| Continual learning | Ported plugin's bun-based stop hook to PowerShell (no bun on this machine); reuses the plugin's `continual-learning` skill / `agents-memory-updater` subagent, only the trigger script changed |

## Next steps (ordered)

1. Schedule/perform §3.8 clean-VM `verify_stack.ps1` run — last Phase 0 invite blocker.
2. Re-check disk space before any Docker image rebuild; if low again, ask user before deleting anything outside Temp/Recycle Bin.
3. 110% plan for Phase 1: §3.7 branch coverage on hot-path modules, §3.3 Playwright E2E.
4. Commit when user asks (bundle docs + ratchet tests + scripts + new continual-learning hook).

## Key paths

- Plan: `PLAN.md`, `docs/MASTER_TODO.md` (§3.10 canonical coverage scope, §3.5/§3.8 status)
- CI: `.github/workflows/test.yml`
- Ratchet tests: `tests/test_coverage_ratchet.py`, `tests/test_sse_inprocess.py`
- New hook: `.cursor/hooks/continual-learning-stop.ps1` (wired in `.cursor/hooks.json` `stop` array)

## Do not re-derive from chat

- Consolidation plan (MASTER §3.10, §8 expansion, `verify_stack.ps1 -WithCoverage`) is **done**.
- Coverage gate §3.5 is **GREEN (95.01%)** — do not re-litigate as open; only §3.8 remains for Phase 0.
