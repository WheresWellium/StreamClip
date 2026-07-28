# Desktop solo gate (no Docker)

Operator tracker for shipping qClip as **Windows + macOS installers only**.  
Docker is optional for self-host operators — not part of this gate.

Companion: [HUMAN_DESKTOP_SMOKE.md](HUMAN_DESKTOP_SMOKE.md) · [DESKTOP_SIGNING.md](DESKTOP_SIGNING.md) · [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)

---

## Phase A — Windows solo smoke

| Step | Command / action | Status |
|------|------------------|--------|
| A1 | `./scripts/fetch_desktop_artifacts.sh v1.0.0-beta.5` (or `.ps1`) | [x] agent 2026-07-28 |
| A2 | Confirm `apps/desktop/release/qClip-Setup-win-x64.exe` exists (~487 MB) | [x] 487 MB fetched |
| A3 | On clean Windows 11: `.\scripts\run_windows_solo_smoke.ps1` (+ [HUMAN_DESKTOP_SMOKE.md](HUMAN_DESKTOP_SMOKE.md)) | ☐ **human host** |
| A4 | Zip logs via smoke script → `tmp/desktop-solo-smoke-win-*/` | ☐ **human host** |
| A5 | Record pass/fail below | ☐ **human host** |

**A evidence**

```
Date: 2026-07-28 (fetch + tooling)
Host: cloud agent (Linux) — installer staged; Explorer smoke NOT run here
Commit / tag: v1.0.0-beta.5 / branch cursor/desktop-first-completion-39d9
Result: FETCH PASS / SMOKE PENDING
Notes: SHA256 fd386ac0e0a1551992e2fcf36a432871a5a4868300aeada47f87efdea0512dc7
       apps/desktop/release/SHA256SUMS.txt · run_windows_solo_smoke.ps1 ready
Log zip path: (pending Windows host)
```

---

## Phase B — macOS DMG

| Step | Command / action | Status |
|------|------------------|--------|
| B1 | On Apple Silicon: `./scripts/build_macos_solo.sh` | ☐ **Mac host** (script ready) |
| B2 | Confirm `apps/desktop/release/qClip-mac-arm64.dmg` | ☐ |
| B3 | Finder smoke: `./scripts/run_macos_solo_smoke.sh` | ☐ |
| B4 | Zip logs via smoke script | ☐ |
| B5 | Record pass/fail below | ☐ |

**B evidence**

```
Date: 2026-07-28 (tooling only)
Host (chip): pending Apple Silicon
Commit: cursor/desktop-first-completion-39d9
Result: TOOLING READY / DMG PENDING
DMG path / size: (run ./scripts/build_macos_solo.sh)
Notes: v1.0.0-beta.5 macos-installer failed: empty CSC_* → "apps/desktop not a file".
       Fixed on this branch: GITHUB_ENV only when secrets non-empty + -c.mac.identity=null.
```

---

## Phase C — Invite kit

| Step | Command / action | Status |
|------|------------------|--------|
| C1 | `./scripts/package_desktop_solo_kit.sh v1.0.0-beta.5` (or `.\scripts\prepare_beta_kit.ps1 -IncludeInstaller`) | [x] agent built kit |
| C2 | Zip contains `installers/qClip-Setup-win-x64.exe` | [x] |
| C3 | Zip contains `installers/qClip-mac-arm64.dmg` when Phase B done | ☐ (Win-only kit until Mac DMG) |
| C4 | Upload zip to Drive / LS / invite channel (not anonymous GitHub) | ☐ **operator** |

Kit path (local): `dist/qclip-beta-kit-DesktopSolo-*.zip` (gitignored).  
Kit also ships desktop-first `docs/BETA_TESTER_QUICKSTART.md` (no “Install Docker Desktop” Step 1).

---

## Phase D — Merge and tag

| Step | Action | Status |
|------|--------|--------|
| D1 | Phase A PASS | ☐ |
| D2 | Phase B PASS (or Mac deferred with written exception) | ☐ |
| D3 | Merge PR #7 → `master` | ☐ |
| D4 | Tag `v1.0.0-beta.6` (triggers desktop-release workflow) | ☐ |
| D5 | Bump [BETA_DOWNLOAD.md](BETA_DOWNLOAD.md) + redeploy henna | ☐ |

Prep script (only after smoke PASS):

```bash
CONFIRM_SOLO_SMOKE=1 ./scripts/finish_desktop_solo_release.sh 1.0.0-beta.6
```

---

## Phase E — Signing (after first cohort)

| Step | Action | Status |
|------|--------|--------|
| E1 | Windows EV / Authenticode — [DESKTOP_SIGNING.md](DESKTOP_SIGNING.md) | ☐ |
| E2 | macOS Developer ID + notarization — [DESKTOP_SIGNING.md](DESKTOP_SIGNING.md) | ☐ |
| E3 | Public download mirror if auto-update required | ☐ |

---

## Gate verdict

| Verdict | When |
|---------|------|
| **GO** | A PASS + B PASS + C kit uploaded |
| **CONDITIONAL GO** | A PASS + Windows kit only; Mac deferred with Gatekeeper docs |
| **NO-GO** | Windows smoke FAIL or installer missing |

*Last updated: 2026-07-28*
