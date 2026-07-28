# Release readiness checklist (operator)

Run before expanding beta cohort or tagging a new desktop release. Companion: `packaging/installer/RELEASE_CHECKLIST.md`, `docs/BETA_GO_LIVE.md`.  
**Human smoke:** [HUMAN_DESKTOP_SMOKE.md](HUMAN_DESKTOP_SMOKE.md) · boot budgets: [DESKTOP_STARTUP.md](DESKTOP_STARTUP.md).  
**Phase E — signing / notarization (post-cohort scripts):** [DESKTOP_SIGNING.md](DESKTOP_SIGNING.md) — not required for first internal solo beta; required before wide cohort.

**Product gate is desktop-first:** Windows `.exe` + macOS `.dmg` are required. Docker/`verify_stack` is an optional operator path, not a beta blocker.  
**Solo gate tracker:** [DESKTOP_SOLO_GATE.md](DESKTOP_SOLO_GATE.md) · kit: `./scripts/package_desktop_solo_kit.sh`

## Engineering gates

- [ ] `.\scripts\verify_coverage.ps1` — ≥95% line on `backend` + `core` (`-m "not desktop"`) *(host Docker or CI; PR coverage job is green)*
- [ ] *(optional)* `.\scripts\verify_stack.ps1` — Docker compose healthy for self-host operators (do **not** wrap with `Tee-Object`)
- [x] PR CI green: coverage, e2e, desktop-smoke (PR #7)
- [x] Alembic head applied in agent/dev env (`0013_license_capabilities`); re-run on each prod host

## Desktop Windows (required)

- [x] `apps/desktop/package.json` version matches tag (`1.0.0-beta.5` / `v1.0.0-beta.5`)
- [x] Artifact name `qClip-Setup-win-x64.exe` + `latest.yml` on GitHub Release
- [x] `docs/BETA_DOWNLOAD.md` version, size, and download notes current (beta.5, ~487 MB)
- [ ] Human smoke (Windows Explorer): [HUMAN_DESKTOP_SMOKE.md](HUMAN_DESKTOP_SMOKE.md) — install → splash→UI → license → short job → play clip → logs
- [x] SmartScreen: documented More info → Run anyway (`BETA_DOWNLOAD.md`, `BETA_KNOWN_ISSUES.md`) until EV signing lands — ops: [DESKTOP_SIGNING.md](DESKTOP_SIGNING.md)
- [ ] EV Authenticode signing for production-quality SmartScreen reputation ([DESKTOP_SIGNING.md](DESKTOP_SIGNING.md): `CSC_*`, `verify_desktop_signing_ready.ps1`, `sign_windows_artifact.ps1`)
- [ ] Logs verified on host: `%LOCALAPPDATA%\qClip\logs\` (`sidecar.log`, `electron.log`)

## Desktop macOS (required)

- [ ] DMG built on Apple Silicon host (`./scripts/build_macos_solo.sh`)
- [ ] Notarization / Developer ID when distributing outside local builds ([DESKTOP_SIGNING.md](DESKTOP_SIGNING.md): `CSC_NAME`/`CSC_LINK`, Apple notary vars, `notarize_macos_artifact.sh`)
- [ ] Human smoke (Finder): [HUMAN_DESKTOP_SMOKE.md](HUMAN_DESKTOP_SMOKE.md)
- [x] Product docs treat DMG as the Mac path (unsigned → right-click Open) until notarized

## Distribution / secrets

- [x] Structlog secret redaction wired (`core/logging_redact.py`); no secrets committed in repo
- [ ] Lemon Squeezy webhook + API key set for activate path (prod)
- [ ] `STREAMCLIP_DISTRIBUTION__TOKEN_ENCRYPTION_KEY` set if YouTube publish enabled
- [x] Private-repo download: testers via invite kit (`.\scripts\prepare_beta_kit.ps1 -IncludeInstaller` → `installers/`), Lemon Squeezy, or operator Drive — collaborators use authenticated `gh release download`; anonymous GitHub URLs 404

## Docs / brand

- [x] User-facing copy is **qClip** only (no StreamClip / Jet Stream in UI)
- [x] Redeploy MkDocs/henna after download-page changes (qClip + beta.5)
- [x] Internal doc links resolve; `docs/SESSION_STATE.md` blockers current

## Go / no-go

**GO** only if Windows `.exe` + macOS `.dmg` artifacts exist, Windows human smoke passes, and the download path works for testers.  
**CONDITIONAL GO** if desktop unsigned / private-download friction remains or macOS DMG is local-only (document in invite email). Docker stack health is optional.  
**NO-GO** if coverage red, license activate broken, or Windows/macOS installer missing.

---

## Last run

| Field | Value |
|-------|-------|
| Date | 2026-07-28 |
| Verdict | **CONDITIONAL GO** |
| Notes | Solo kit built (Win exe inside `dist/qclip-beta-kit-DesktopSolo-*.zip`). Open: Windows Explorer smoke, Mac `build_macos_solo.sh`, kit upload, then merge/tag beta.6. Signing: [DESKTOP_SIGNING.md](DESKTOP_SIGNING.md). Tracker: [DESKTOP_SOLO_GATE.md](DESKTOP_SOLO_GATE.md). |
