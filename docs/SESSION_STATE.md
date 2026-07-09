# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-08 (Windows+Mac Docker docs + macOS scaffold)

## Active chats

| Branch | Task | Lock id | Notes |
|--------|------|---------|-------|
| `master` (local dirty) | macOS scaffold + beta docs | — | See `docs/AGENT_COORDINATION.md` |

## Current focus

**Beta install docs:** `BETA_DOWNLOAD.md` + quickstart now cover **Windows and Mac Docker** (no Apple Dev account). One-click `.exe`/`.dmg` still “coming soon.”

**Windows beta:** v1.0.0-beta.2 at `apps/desktop/release/StreamClip-Setup-win-x64.exe`. **Pending:** `gh release create`.

**macOS (§5) scaffold:** Application Support path, arm64 DMG config, build script — no DMG artifact yet.

## Blockers

- `gh` not on PATH for Windows release publish
- macOS DMG needs a Mac host

## Next steps (ordered)

1. Redeploy docs so Vercel shows Mac tab: `streamclip-henna.vercel.app/BETA_DOWNLOAD/`
2. Publish Windows installer when `gh` available
3. Mac host: `./scripts/build_desktop_installer_macos.sh`
4. §5.1/5.2 ffmpeg VideoToolbox + arm64 ML

## Key paths

- Download (users): `docs/BETA_DOWNLOAD.md` · Builders: `docs/MACOS_INSTALLER.md`
- Mac build: `scripts/build_desktop_installer_macos.sh` · `packaging/installer/MACOS.md`
- Win installer: `scripts/build_desktop_installer.ps1`
