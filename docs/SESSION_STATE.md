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

- **Windows installer published:** [v1.0.0-beta.5](https://github.com/WheresWellium/StreamClip/releases/tag/v1.0.0-beta.5) — asset `qClip-Setup-win-x64.exe` (~487 MB) + `latest.yml` (path: `qClip-Setup-win-x64.exe`).
- CI: Desktop release run success for windows-installer; macos-installer failed (unsigned / known scaffold, continue-on-error).
- Repo is **private** — anonymous `/releases/latest/download/...` 404s without auth; authenticated/`gh release download` works.

## Next steps

1. Optional: redeploy MkDocs so henna `BETA_DOWNLOAD` shows beta.5.
2. Publisher OAuth polish; coverage/stack gates.
3. macOS DMG when Apple Silicon signing path is ready.

## Key paths

- Brand UI: `web/app/layout.tsx`, splash, onboarding, Settings
- Installer: `apps/desktop/package.json`
- Docs: `docs/BETA_DOWNLOAD.md`, `mkdocs.yml`, tutorials
