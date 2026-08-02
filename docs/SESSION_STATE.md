# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-31 (desktop-first mastery audit)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `master` | beta.7 ship | — | pipeline UX + auth in `v1.0.0-beta.7` exe |
| `master` | desktop mastery audit | — | TDD Rev 5 desktop-primary; taxonomy + clean-desktop-VM gate |

## Desktop-first finish line — SHIPPED (2026-07-31)

- **Product = the installer.** TDD Rev 5 desktop-primary; Docker → Appendix D. Decision: harden, don't rewrite. Gap rev 11.
- **Turnkey pre-ship command (green end-to-end):** `.\scripts\verify_desktop_release.ps1` — chains coverage F10 (91%), upgrade F5, clean-boot F1/F12, signing readiness F9; then prints the operator-only clean-VM + cohort checklist.
- **Desktop beta exit (MASTER §8.16d):** [DESKTOP_COHORT_EXIT.md](DESKTOP_COHORT_EXIT.md) — crash-free >98% (7d) + install→first-clip <45m median. Docker Phase 0 pack retained only for Pro/self-host.
- **Code residues closed:** F1 (writable hard-exit), F4 (failure-reason.ts + boot-failure propagation, 6+1 tests), F6 (classify_failure + Retry banner + POST /api/health/models/retry, 17 tests).
- **🔴 NEW P0 (2026-08-01) — F13 feedback black hole:** desktop in-app bug reports/feedback are never delivered (env-only `OPS_WEBHOOK_URL`/`SMTP_HOST` unset on desktop → `_queue_support_notifications` dispatches nothing; row stays in the tester's local SQLite; UI says "we'll review it"). **Blocks cohort invites.** Direction chosen: **hosted collector on existing Vercel project**. Tracked: MASTER §4.22, taxonomy F13, GAP D11. Not implemented — infra decision pending.
- **Residue (operator only):** F9 EV cert purchase (O11); clean-VM install→first-clip sign-off; cohort numbers. Do not invent.
- Scope lock: FS-3 + roadmap (diarization/IG/TikTok direct) deferred post-launch.

## Readiness

| Metric | % | Notes |
|--------|---|-------|
| Tester-ready **shipped** | **~95%** | Win installer **beta.7** live (2026-07-31) |
| Phase 0 **exit** | **~70%** | O4/O5/O11; Mac universal ☐; notarize/EV ☐ |

## Shipped in beta.7

- Stuck-job error surfacing (`ProgressTask.on_failure` + in-process worker)
- Status filter “Processing” → ingesting/transcribing/detecting
- Link Jobs modal event-driven (Settings only)
- Auth: password policy, 409 duplicate email, auth rate limit, forgot/reset pending UX
- Prior: license LocalAppData path, SPA job shells, header Back, white-screen fix

## Download

https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe

## Deferred

Email verification · session kill on reset · HttpOnly refresh · desktop Sentry · Mac universal

## Next steps

1. Testers: uninstall old → install beta.7 → retest license, Twitch→progress, filters, auth
2. O4 / O5 human gates
3. Mac universal when ready
