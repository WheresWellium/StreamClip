# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-08 (desktop v1.0.0-beta.2 build — auth UX)

## Current focus

**Phase 0 ops (no n8n):** `issue_beta_keys.py` (`--tier admin` for max access), `grant_dev_pro.py`, `list_support_reports.py`, `BETA_OPS_PHASE0.md`; web license uses browser device id.

**Creator distribution:** Windows **v1.0.0-beta.2** (auth UX) via GitHub Releases + Vercel docs (`docs/BETA_DOWNLOAD.md`).

## Blockers

- EV code signing optional for beta (SmartScreen warning documented)

## Next steps (ordered)

1. Finish `publish_desktop_release.ps1 -Version 1.0.0-beta.2` (build + gh release)
2. Vercel docs live at `streamclip-henna.vercel.app/BETA_DOWNLOAD/` (`streamclip.vercel.app` is a stale alias — do not share)
3. Send waitlist the Vercel download URL

## Key paths

- Ops runbook: `docs/BETA_OPS_PHASE0.md`
- Beta keys: `scripts/issue_beta_keys.py`
- Support triage: `scripts/list_support_reports.py`, `GET /api/admin/bug-reports`
- Download page: `docs/BETA_DOWNLOAD.md` → `/BETA_DOWNLOAD/`
- CI: `.github/workflows/desktop-release.yml`
- Installer: `apps/desktop/release/StreamClip-Setup-win-x64.exe`
- Publish script: `scripts/publish_desktop_release.ps1`
