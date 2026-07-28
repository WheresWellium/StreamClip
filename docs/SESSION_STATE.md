# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-28

## Active chats

| Chat | Branch | Focus |
|------|--------|-------|
| cloud-desktop-first | `cursor/desktop-first-completion-39d9` | Release readiness + qClip desktop-first |

## Current focus

**Release readiness pass** on desktop-first / qClip branch. External brand is **qClip** only. GitHub host path remains `WheresWellium/StreamClip`.

## Blockers

- EV Authenticode cert — SmartScreen until signed.
- macOS DMG + notarization — Apple Silicon host + Developer ID.
- Phase 0 exit — T0 cohort metrics (MASTER §8.16); engineering invite gate already cleared.
- Private GitHub repo — anonymous release download URLs 404; need auth, invite zip, or public mirror.

## Validation

- **Windows installer:** [v1.0.0-beta.5](https://github.com/WheresWellium/StreamClip/releases/tag/v1.0.0-beta.5) — `qClip-Setup-win-x64.exe` (~487 MB) + `latest.yml`.
- PR #7 CI: coverage / e2e / desktop-smoke / Vercel **green** on `3f4f343+`.
- macOS installer CI: failed unsigned scaffold (`continue-on-error`).
- Local: license/middleware/quota tests pass; full Docker `verify_stack.ps1` not runnable in this Linux cloud agent (no Docker).

## Next steps

1. Redeploy MkDocs/henna so public BETA_DOWNLOAD shows qClip + beta.5.
2. Mirror or auth-gate Windows installer for testers without GitHub access.
3. macOS DMG when Apple Silicon signing path is ready.
4. Human validation checklists for Windows Explorer install + macOS Finder launch.

## Key paths

- Brand UI: `web/app/layout.tsx`, splash, onboarding, Settings
- Installer: `apps/desktop/package.json`
- Docs: `docs/BETA_DOWNLOAD.md`, `docs/RELEASE_CHECKLIST.md`, `mkdocs.yml`
