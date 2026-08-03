# Clean-desktop-VM verification (product ship gate)

**Purpose:** prove the **installer** — the thing testers actually run — reaches "first clip" on a **fresh Windows 11 machine with no prior qClip data**. This is the product gate. It replaces Docker [CLEAN_VM_VERIFY.md](CLEAN_VM_VERIFY.md) as the blocker for desktop releases; the Docker verify remains only for contributors and the future Pro self-host SKU.

Why this exists: the Docker clean-VM gate proved `docker compose up`, not the `.exe`. That is the exact reason "works on my machine, breaks for other Windows users" kept recurring (see [DESKTOP_FAILURE_TAXONOMY.md](DESKTOP_FAILURE_TAXONOMY.md) F11).

## Prerequisites

- Windows 11 VM from a **clean snapshot** — no `%LOCALAPPDATA%\StreamClip`, no prior install, no dev repo.
- The **built** `qClip-Setup-win-x64.exe` for the commit/tag you intend to ship (from `scripts/publish_desktop_release.ps1` output or the GitHub release).
- A short test source: a local `.mp4` (< 2 min) or a short Twitch/YouTube clip URL.

## Automated pre-flight (ONE command on the build host)

Run the turnkey pre-ship gate. It chains every automatable check and then prints the operator-only manual steps:

```powershell
.\scripts\verify_desktop_release.ps1                 # unsigned beta
.\scripts\verify_desktop_release.ps1 -RequireSigning # signed release
```

It runs, blocking on any failure:

1. `verify_desktop.ps1` — profile smoke + **seam coverage gate** (F10) + **upgrade simulation** (F5)
2. `verify_desktop_clean.ps1` — fresh-data-dir sidecar boot (F1/F5/F12): temp `STREAMCLIP_DESKTOP_DATA_DIR`, boot, `/api/health`, migrations + writable dirs, teardown
3. `verify_desktop_signing_ready.ps1` — signing readiness (F9; informational unless `-RequireSigning`)

Then it prints the **operator-only** checklist below (build/sign/publish + clean-VM install + cohort numbers) — those are human evidence and are intentionally never auto-filled.

## Manual gate (run on the clean VM)

Do these in order. **Stop and file a taxonomy row on the first failure.**

1. **Install.** Double-click `qClip-Setup-win-x64.exe`. On SmartScreen: **More info → Run anyway** (expected until EV signing — F9). Accept the default install location.
2. **First launch.** Tray icon appears; window shows the **dark splash**, never a blank white screen (F1/F4). If you see "qClip could not start its local engine", the gate has failed — open the engine log from the error page and capture it.
3. **Models warm.** The model-warmup banner completes (first run downloads ~1.5 GB — F6). Confirm no eternal spinner.
4. **License activate.** Paste a cohort/test key → activation succeeds (no 500 — F1). Confirm perpetual expiry shows.
5. **First clip.** Create a job from the short source. Watch live progress (SSE via the in-process bus — F10). Job reaches **done** with at least one downloadable clip.
6. **Play + download.** A clip plays in-app and downloads (LocalStorage `/storage/{key}` same-origin — static UI mount).
7. **Restart.** Quit fully (tray → Quit), relaunch. The prior job/clip is still present (SQLite persisted in `%LOCALAPPDATA%\StreamClip`).
8. **Upgrade path (when applicable).** Install the previous beta first, create a job, then install the new build over it. Confirm migrations apply, the old job survives, and the license does not need re-entry (F5).

## Capture on failure

From the VM, collect:

- `%LOCALAPPDATA%\StreamClip\workspace\` listing and `streamclip.db` presence
- Electron engine log: tray → **Open engine log** (or `%APPDATA%\qClip\logs\sidecar.log`)
- Screenshot of the failing screen
- The taxonomy ID it maps to ([DESKTOP_FAILURE_TAXONOMY.md](DESKTOP_FAILURE_TAXONOMY.md))

## Pass criteria

| Check | Required |
|-------|----------|
| Automated pre-flight `verify_desktop_clean.ps1` | Yes |
| Install + first launch, no white screen | Yes |
| License activate (no 500) | Yes |
| Short source → job `done` with a playable clip | Yes |
| Clip download works | Yes |
| Restart preserves data | Yes |
| Upgrade-from-previous-beta (when a prior build exists) | Yes for updates |
| SmartScreen "Run anyway" documented | Until EV signing (F9) |

## Sign-off template

```
Clean-desktop-VM verify (product gate)
VM: Windows 11 __________  Snapshot: __________
Installer: qClip-Setup-win-x64.exe  build/tag: v1.0.0-beta.20  Commit: 5174abb / 324f1d1
verify_desktop_clean.ps1: PASS / FAIL
Install + first launch (no white screen): PASS / FAIL
License activate: PASS / FAIL
Short source -> first clip: PASS / FAIL   (job_id: __________)
Clip download: PASS / FAIL
Restart persistence: PASS / FAIL
Upgrade-from-previous: PASS / FAIL / N/A
Tester: __________  Date (UTC): __________
```

## Build-host preflight (beta.20) — not a VM substitute

Recorded 2026-08-03 on the build host (agent):

```
verify_desktop_release.ps1 (unsigned): PASS
  - seam coverage F10: PASS (91.71%)
  - upgrade simulation F5: PASS
  - verify_desktop_clean.ps1 F1/F12: PASS
  - signing preflight: unsigned path OK (EV cert not present)
```

Manual steps 1–7 above remain **operator-only** on a clean Win11 snapshot. Do not invent Pass for those rows.
See also [`docs/evidence/clean-desktop-vm-beta20.md`](evidence/clean-desktop-vm-beta20.md).
