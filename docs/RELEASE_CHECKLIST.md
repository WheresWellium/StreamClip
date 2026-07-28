# Release readiness checklist (operator)

Run before expanding beta cohort or tagging a new desktop release. Companion: `packaging/installer/RELEASE_CHECKLIST.md`, `docs/BETA_GO_LIVE.md`.  
**Human smoke:** [HUMAN_DESKTOP_SMOKE.md](HUMAN_DESKTOP_SMOKE.md) · boot budgets: [DESKTOP_STARTUP.md](DESKTOP_STARTUP.md).

## Engineering gates

- [ ] `.\scripts\verify_coverage.ps1` — ≥95% line on `backend` + `core` (`-m "not desktop"`) *(host Docker; PR coverage job is green)*
- [ ] `.\scripts\verify_stack.ps1` — Docker stack healthy (do **not** wrap with `Tee-Object`)
- [x] PR CI green: coverage, e2e, desktop-smoke (PR #7)
- [x] Alembic head applied in agent/dev env (`0013_license_capabilities`); re-run on each prod host

## Desktop Windows

- [x] `apps/desktop/package.json` version matches tag (`1.0.0-beta.5` / `v1.0.0-beta.5`)
- [x] Artifact name `qClip-Setup-win-x64.exe` + `latest.yml` on GitHub Release
- [x] `docs/BETA_DOWNLOAD.md` version, size, and download notes current (beta.5, ~487 MB)
- [ ] Human smoke (Windows Explorer): [HUMAN_DESKTOP_SMOKE.md](HUMAN_DESKTOP_SMOKE.md) — install → splash→UI → license → short job → play clip → logs
- [x] SmartScreen: documented More info → Run anyway (`BETA_DOWNLOAD.md`, `BETA_KNOWN_ISSUES.md`) until EV signing lands
- [ ] EV Authenticode signing for production-quality SmartScreen reputation
- [ ] Logs verified on host: `%LOCALAPPDATA%\qClip\logs\` (`sidecar.log`, `electron.log`)

## Desktop macOS

- [ ] DMG built on Apple Silicon host (`./scripts/build_desktop_installer_macos.sh`)
- [ ] Notarization / Developer ID when distributing outside local builds
- [ ] Human smoke (Finder): [HUMAN_DESKTOP_SMOKE.md](HUMAN_DESKTOP_SMOKE.md)
- [x] Until ready: BETA_DOWNLOAD macOS row kept as Coming soon

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

**GO** only if engineering gates + Windows human smoke pass and download path works for testers.  
**CONDITIONAL GO** if Docker path is solid but desktop unsigned / private-download friction remains (document in invite email).  
**NO-GO** if coverage/stack red, license activate broken, or installer missing.

---

## Last run

| Field | Value |
|-------|-------|
| Date | 2026-07-28 |
| Verdict | **CONDITIONAL GO** |
| Notes | Polish pass: desktop `logs/sidecar.log`+`electron.log`, pipeline claim/idempotency, invite `-IncludeInstaller`, brand/API/email qClip, henna live. Still open: Windows Explorer human smoke, EV signing, macOS notarization, Docker `verify_stack` on clean VM, LS prod secrets. |
