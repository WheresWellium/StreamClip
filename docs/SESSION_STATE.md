# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-31 (auth hardening #5)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `cursor/pipeline-and-ux-fixes` | #5 auth robustness | — | password policy, 409 register, auth rate limit, forgot/reset UX |

## Readiness

| Metric | % | Notes |
|--------|---|-------|
| Tester-ready **shipped** | **~92%** | Live `.exe` still **pre** pipeline/UX/auth WIP — needs republish |
| Phase 0 **exit** | **~70%** | O4/O5/O11; Mac universal ☐; notarize/EV ☐ |

## On this branch (not yet merged)

1. Stuck jobs → `ProgressTask.on_failure` + in-process worker
2. Status filter “Processing” → ingesting/transcribing/detecting
3. Link Jobs modal → event-driven only (Settings button)
4. **#5 Auth:** `core/password_policy.py`, 409 duplicate email, `rate_limit_auth`, client policy + pending forgot/reset

## Deferred (auth architecture)

Email verification before license claim · token_version/session kill · HttpOnly refresh cookie · desktop Sentry SDK

## Blockers (human-only)

- O4 cohort exit · O5 on-call · O11 EV signing
- Mac universal upload · notarization

## Next steps

1. Finish verify #5 tests → commit/merge `cursor/pipeline-and-ux-fixes`
2. Republish Windows installer (`publish_desktop_release.ps1`) + bump `docs/BETA_DOWNLOAD.md`
3. Retest: license, Twitch → progress, status filter, no Link Jobs on boot, Back, register/reset
