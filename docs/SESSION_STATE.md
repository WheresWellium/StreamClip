# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-28

## Active chats

| Chat | Branch | Focus |
|------|--------|-------|
| cloud-desktop-first | `cursor/desktop-first-completion-39d9` | Henna consolidated → human smoke remaining |

## Current focus

**One creator guide:** `docs/GET_STARTED.md` — install, license, first clip, FAQ. Legacy pages stubbed + redirected. Live after merge to `master`.

## Henna (published nav)

- Home → **Get started** → Guides → Help → For builders
- Excluded: BETA_DOWNLOAD, BETA_TESTER_QUICKSTART, DESKTOP_SOLO_USER_GUIDE, TUTORIAL_INSTALL (redirects → GET_STARTED)

## Agent-complete

- Consolidation: GET_STARTED.md, mkdocs redirects, web Help menu, kit scripts, email templates
- Desktop solo kit: `dist/qclip-beta-kit-DesktopSolo-*.zip`
- Win exe staged; macOS CI fix on branch

## Human remaining

1. Windows: `.\scripts\run_windows_solo_smoke.ps1`
2. Mac: `./scripts/build_macos_solo.sh` + smoke
3. `CONFIRM_SOLO_SMOKE=1 ./scripts/finish_desktop_solo_release.sh 1.0.0-beta.6`
4. Merge PR #7; tag `v1.0.0-beta.6`

## Key paths

- Creator guide: `docs/GET_STARTED.md`
- Gate: `docs/DESKTOP_SOLO_GATE.md`
- Henna config: `mkdocs.yml`
