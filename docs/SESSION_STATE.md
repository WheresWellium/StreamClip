# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-31 (beta.7 published)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `master` | beta.7 ship | — | pipeline UX + auth in `v1.0.0-beta.7` exe |

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
