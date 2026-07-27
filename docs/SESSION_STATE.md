# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-27

## Active chats

| Chat | Branch | Focus |
|------|--------|-------|
| cloud-desktop-first | `cursor/desktop-first-completion-39d9` | qClip brand lock + desktop-first |

## Current focus

**qClip brand lock** — external UI, installers, published docs, and emails use **qClip** only. Users must not see StreamClip or Jet Stream. GitHub repository path remains `WheresWellium/StreamClip` (hosting only).

## Blockers

- EV Authenticode cert — SmartScreen until signed.
- macOS DMG + notarization — Apple Silicon host + Developer ID.
- Phase 0 exit — T0 cohort; clean-VM `verify_stack.ps1`.
- Republish Windows installer so GitHub Releases asset is `qClip-Setup-win-x64.exe`.

## Validation

- Webhook signature header `X-qClip-Signature` tests pass.
- UI/header/splash/onboarding/billing show qClip.
- Installer `productName` / NSIS / `appId` (`io.qclip.desktop`) / artifacts → qClip.

## Next steps

1. Republish desktop release so download URLs resolve to `qClip-Setup-win-x64.exe`.
2. Optional: rename GitHub repo when ready (docs links still use current path).
3. Publisher OAuth polish; full coverage/stack gates.

## Key paths

- Brand UI: `web/app/layout.tsx`, splash, onboarding, Settings
- Installer: `apps/desktop/package.json`
- Docs: `docs/BETA_DOWNLOAD.md`, `mkdocs.yml`, tutorials
