# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-08-03 (open items close-out)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `master` | open-items close-out | — | F13 closed; EV + clean-VM operator |

## Closed this pass

| Item | Evidence |
|------|----------|
| TikTok IP docs | `BETA_KNOWN_ISSUES` + troubleshooting |
| Build-host preflight beta.20 | `verify_desktop_release.ps1` PASS |
| F13 henna SMTP | Vercel env synced; `GET/POST` email `delivered`; packaged `ops_notification=queued` |
| Render P0 (prior) | beta.20 hardened Pass |

## Still operator-gated

| Item | State |
|------|-------|
| Clean-VM install→first-clip | Preflight PASS; manual sign-off ☐ — `docs/evidence/clean-desktop-vm-beta20.md` |
| EV signing | Explicitly blocked — no `CSC_THUMBPRINT`; `-RequireSigned` fail-closed |

## Download

Latest → **1.0.0-beta.20**  
https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe
