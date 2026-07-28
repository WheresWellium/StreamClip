# Human desktop smoke (operator / tester)

Manual pass on a real Windows or macOS host before expanding the beta cohort.  
**Primary beta path:** desktop installers (`qClip-Setup-win-x64.exe`, `qClip-mac-arm64.dmg`) — **no Docker required**. Docker compose remains an optional operator/self-host path.  
Boot budgets and in-app checks: [DESKTOP_STARTUP.md](DESKTOP_STARTUP.md).  
Download / SmartScreen notes: [BETA_DOWNLOAD.md](BETA_DOWNLOAD.md).  
**Gate tracker:** [DESKTOP_SOLO_GATE.md](DESKTOP_SOLO_GATE.md).

**One-command helpers**

```powershell
# Windows (clean host)
.\scripts\fetch_desktop_artifacts.ps1 -Tag v1.0.0-beta.5
.\scripts\run_windows_solo_smoke.ps1
```

```bash
# macOS Apple Silicon
./scripts/build_macos_solo.sh
./scripts/run_macos_solo_smoke.sh
```

---

## Windows (Explorer)

| Step | Pass? |
|------|-------|
| 1. Get `qClip-Setup-win-x64.exe` from invite kit `installers/`, Lemon Squeezy, or operator Drive (not anonymous GitHub) | ☐ |
| 2. Double-click in Explorer → install completes | ☐ |
| 3. SmartScreen (unsigned): **More info → Run anyway** | ☐ |
| 4. Start menu → **qClip** → splash shows **qClip**, then main UI (maximized, no menu bar) | ☐ |
| 5. Settings → activate license key → capabilities listed | ☐ |
| 6. Run one short job (small local file or short URL) → status completes | ☐ |
| 7. Open / play a rendered clip in-app | ☐ |
| 8. Locate logs (below) | ☐ |

**Logs (Windows)**

```
%LOCALAPPDATA%\qClip\logs\
  sidecar.log
  electron.log
```

If an older install reused the legacy folder: `%LOCALAPPDATA%\StreamClip\logs\`.  
App data (DB, workspace) sits alongside under `%LOCALAPPDATA%\qClip\` — see [DESKTOP_STARTUP.md](DESKTOP_STARTUP.md).

---

## macOS (Finder)

| Step | Pass? |
|------|-------|
| 1. Open `.dmg` from Finder (when a build is available; public row is Coming soon) | ☐ |
| 2. Drag **qClip** to Applications (or open from the volume) | ☐ |
| 3. Gatekeeper (unsigned): **right-click → Open** → Open | ☐ |
| 4. Launch → splash **qClip** → main UI | ☐ |
| 5. Activate license key | ☐ |
| 6. One short job → completes | ☐ |
| 7. Play a rendered clip | ☐ |
| 8. Locate logs (below) | ☐ |

**Logs (macOS)**

```
~/Library/Application Support/qClip/logs/
  sidecar.log
  electron.log
```

App data: `~/Library/Application Support/qClip/`.

---

## Evidence capture (required for DESKTOP_SOLO_GATE)

After a pass or fail, record results in [DESKTOP_SOLO_GATE.md](DESKTOP_SOLO_GATE.md).

**Windows — zip logs**

```powershell
$logDir = Join-Path $env:LOCALAPPDATA "qClip\logs"
if (-not (Test-Path $logDir)) { $logDir = Join-Path $env:LOCALAPPDATA "StreamClip\logs" }
Compress-Archive -Path $logDir -DestinationPath "$env:USERPROFILE\Desktop\qclip-smoke-win-logs.zip" -Force
Write-Host "Wrote Desktop\qclip-smoke-win-logs.zip"
```

**macOS — zip logs**

```bash
LOGDIR="$HOME/Library/Application Support/qClip/logs"
test -d "$LOGDIR" || LOGDIR="$HOME/Library/Application Support/StreamClip/logs"
zip -r ~/Desktop/qclip-smoke-mac-logs.zip "$LOGDIR"
echo "Wrote ~/Desktop/qclip-smoke-mac-logs.zip"
```

---

## Fail / escalate

- Splash never appears, or blank wait past cold budget → capture `electron.log` + `sidecar.log` and file in-app **Report a bug**.
- License activate fails → note key prefix + HTTP status (do not paste full key in public channels).
- Job stuck → job id + both log files.
