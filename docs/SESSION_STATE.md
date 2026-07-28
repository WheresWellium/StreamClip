# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-28

## Active chats

| Chat | Branch | Focus |
|------|--------|-------|
| cloud-desktop-first | `cursor/desktop-first-completion-39d9` | Release readiness + qClip desktop-first |

## Current focus

**Release checklist polish** on `cursor/desktop-first-completion-39d9`. Verdict still **CONDITIONAL GO**. Brand **qClip** only.

## Blockers

- Human Windows Explorer smoke ([HUMAN_DESKTOP_SMOKE.md](HUMAN_DESKTOP_SMOKE.md)).
- EV Authenticode / SmartScreen.
- macOS DMG + notarization.
- Docker `verify_stack.ps1` on operator host (no Docker in this agent).

## Validation

- beta.5 Windows installer + PR CI green; henna qClip/beta.5 live.
- Shipped: desktop file logs, pipeline claim + highlights skip, log redaction, `-IncludeInstaller` kit, brand/API polish.
- Alembic head `0013_license_capabilities` in agent env.

## Next steps

1. Human Windows smoke + zip logs from `%LOCALAPPDATA%\qClip\logs\`.
2. `.\scripts\prepare_beta_kit.ps1 -IncludeInstaller` for tester distribution.
3. EV cert; macOS DMG when ready.
4. Merge PR #7 when human smoke signs off.

## Key paths

- Logs: `desktop_sidecar/run.py`, `apps/desktop/src/main.ts`
- Claim: `JobRepository.try_claim_pipeline`, `start_pipeline`
- Docs: `RELEASE_CHECKLIST.md`, `HUMAN_DESKTOP_SMOKE.md`, `BETA_DOWNLOAD.md`
- Kit: `scripts/prepare_beta_kit.ps1 -IncludeInstaller`
