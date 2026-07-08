# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-08 (Figma layout pass — zero overlap verified)

## Current focus

**Phase 0 ops (no n8n):** `issue_beta_keys.py` (`--tier admin` for max access), `grant_dev_pro.py`, `list_support_reports.py`, `BETA_OPS_PHASE0.md`; web license uses browser device id.

**Creator distribution (parallel):** Windows `.exe` via GitHub Releases + Vercel docs (`docs/BETA_DOWNLOAD.md`).

## Blockers

- **First GitHub Release** — installer not published until `build_desktop_installer.ps1` + `publish_desktop_release.ps1` or `desktop-release` workflow runs
- Download button 404 until release exists at `.../StreamClip-Setup-win-x64.exe`
- EV code signing optional for beta (SmartScreen warning documented)

## Next steps (ordered)

1. Build: `.\scripts\build_desktop_installer.ps1` (~30–60 min, ~15 GB disk)
2. Publish: `.\scripts\publish_desktop_release.ps1` or push tag `v1.0.0-beta.1` (CI workflow)
3. Deploy docs: commit + push → Vercel auto-builds `streamclip.vercel.app/BETA_DOWNLOAD/`
4. Send waitlist the Vercel download URL

## Key paths

- Ops runbook: `docs/BETA_OPS_PHASE0.md`
- Beta keys: `scripts/issue_beta_keys.py`
- Support triage: `scripts/list_support_reports.py`, `GET /api/admin/bug-reports`
- Download page: `docs/BETA_DOWNLOAD.md` → `/BETA_DOWNLOAD/`
- CI: `.github/workflows/desktop-release.yml`
- Installer: `apps/desktop/release/StreamClip-Setup-win-x64.exe`
- Publish script: `scripts/publish_desktop_release.ps1`
