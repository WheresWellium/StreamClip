# Release readiness checklist (operator)

Run before expanding beta cohort or tagging a new desktop release. Companion: `packaging/installer/RELEASE_CHECKLIST.md`, `docs/BETA_GO_LIVE.md`.

## Engineering gates

- [ ] `.\scripts\verify_coverage.ps1` — ≥95% line on `backend` + `core` (`-m "not desktop"`)
- [ ] `.\scripts\verify_stack.ps1` — Docker stack healthy (do **not** wrap with `Tee-Object`)
- [ ] PR CI green: coverage, e2e, desktop-smoke
- [ ] Alembic head applied in target env (`alembic upgrade head`)

## Desktop Windows

- [ ] `apps/desktop/package.json` version matches tag (`1.0.0-beta.N`)
- [ ] Artifact name `qClip-Setup-win-x64.exe` + `latest.yml` on GitHub Release
- [ ] `docs/BETA_DOWNLOAD.md` version, size, and download notes current
- [ ] Human smoke (Windows host): Explorer install → Start menu launch → license activate → 1 short job → clip playable
- [ ] SmartScreen: document More info → Run anyway until EV signing lands
- [ ] Logs: `%LOCALAPPDATA%\qClip\` (or legacy `StreamClip` if reused)

## Desktop macOS

- [ ] DMG built on Apple Silicon host (`./scripts/build_desktop_installer_macos.sh`)
- [ ] Notarization / Developer ID when distributing outside local builds
- [ ] Human smoke: Finder open → first run → license → short job
- [ ] Until ready: keep BETA_DOWNLOAD macOS row as Coming soon

## Distribution / secrets

- [ ] No secrets in repo or logs (`STREAMCLIP_*` via env / `.env`)
- [ ] Lemon Squeezy webhook + API key set for activate path
- [ ] `STREAMCLIP_DISTRIBUTION__TOKEN_ENCRYPTION_KEY` set if YouTube publish enabled
- [ ] Private-repo download: invite zip or authenticated `gh release download` — anonymous URLs 404

## Docs / brand

- [ ] User-facing copy is **qClip** only (no StreamClip / Jet Stream in UI)
- [ ] Redeploy MkDocs/henna after download-page changes
- [ ] Internal doc links resolve; `docs/SESSION_STATE.md` blockers current

## Go / no-go

**GO** only if engineering gates + Windows human smoke pass and download path works for testers.  
**CONDITIONAL GO** if Docker path is solid but desktop unsigned / private-download friction remains (document in invite email).  
**NO-GO** if coverage/stack red, license activate broken, or installer missing.
