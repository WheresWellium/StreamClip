# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-27

## Active chats

| Chat | Branch | Focus |
|------|--------|-------|
| cloud-desktop-first | `cursor/desktop-first-completion-39d9` | Desktop-first plan + qClip rebrand |

## Current focus

**Desktop-first completion** (plan `desktop_first_completion_df79ca40`): one Windows `.exe`, capability licenses, fast boot, hardware onboarding, local storage UX. External brand: **qClip** (wipe StreamClip / Jet Stream from user-facing UI).

## Blockers

- EV Authenticode cert (§4.10) — SmartScreen until signed.
- macOS DMG + notarization — Apple Silicon host + Developer ID.
- Phase 0 exit — T0 cohort (§8.16); clean-VM `verify_stack.ps1`.

## Validation (this branch)

- Quota + license revocation tests: passed.
- Device profile + storage status + health stack + sidecar packaging: 29 passed.
- Desktop `tsc --noEmit` clean (prior commit).
- Alembic `0012_quota_period_start` on branch.

## Next steps (plan order)

1. WS1 capability entitlements (`studio` / `publisher` / `audio_ingest`).
2. WS5 publisher OAuth after first clip; WS6 E2E/perf gates.
3. Finish remaining StreamClip/Jet Stream strings in operator docs.
4. Windows smoke: splash → maximized frameless → device recommendation → local path.

## Key paths

- Desktop: `apps/desktop/src/main.ts`, `splash.html`, `package.json`
- Quotas: `backend/services/quota.py`, `alembic/versions/0012_quota_period_start.py`
- Licensing: `core/licensing.py`, `backend/api/license.py`
- Brand UI: `web/app/layout.tsx`, onboarding, sidecar gate
