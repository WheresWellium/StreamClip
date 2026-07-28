# qClip desktop — step-by-step (no Docker)

**You do not need Docker.** Install the desktop app for your OS, activate your license, run one short job.

| | Windows | macOS |
|--|---------|-------|
| Installer | `qClip-Setup-win-x64.exe` (~487 MB) | `qClip-mac-arm64.dmg` (Apple Silicon) |
| Current tag | `v1.0.0-beta.5` | Build on Mac when DMG not in kit yet |
| First-run friction | SmartScreen → **More info → Run anyway** | Gatekeeper → **right-click → Open** |
| Logs | `%LOCALAPPDATA%\qClip\logs\` | `~/Library/Application Support/qClip/logs/` |

Get the file from your **invite kit** (`installers/`), **Drive** link, or **Lemon Squeezy** — not from a public GitHub download URL (private repo → 404).

---

## Part 1 — Windows (you)

### What you need

- Windows 10 or 11 (64-bit)
- ~16 GB RAM (32 GB better)
- NVIDIA GPU recommended (CPU works, slower)
- License key from invite email (`SCPRO-…`)
- Installer: `qClip-Setup-win-x64.exe`

### Steps

1. **Get the installer**  
   Open your invite kit zip → `installers\qClip-Setup-win-x64.exe`  
   (Or use the Drive / Lemon Squeezy link from your invite.)

2. **Run the installer**  
   Double-click the `.exe` in Explorer.

3. **If SmartScreen appears** (“Windows protected your PC”)  
   - Click **More info**  
   - Click **Run anyway**  
   This is expected for the unsigned beta. It is not a virus warning you must ignore forever — signing comes later.

4. **Finish setup**  
   Accept defaults → Install → Finish.

5. **Launch qClip**  
   Start menu → **qClip**.  
   Wait for splash → main UI (first launch may download models; allow time and disk).

6. **Confirm ready**  
   **Settings → Get started** → should show **Ready**.  
   If **Needs attention**, open **Help → Troubleshooting** before creating jobs.

7. **Activate license**  
   **Settings → License** → paste `SCPRO-…` → **Activate**.

8. **First clip (smoke)**  
   - **New job**  
   - Paste a **short public** YouTube/Twitch URL (or a small local file)  
   - Submit and wait until status is **done**  
   - Open / play one rendered clip in-app  

9. **Confirm logs exist**  
   Open File Explorer and go to:

   ```
   %LOCALAPPDATA%\qClip\logs\
   ```

   You should see `sidecar.log` and `electron.log`.

### Optional — one script (if you have the repo)

```powershell
.\scripts\fetch_desktop_artifacts.ps1 -Tag v1.0.0-beta.5
.\scripts\run_windows_solo_smoke.ps1
```

### Zip logs for support

```powershell
$logDir = Join-Path $env:LOCALAPPDATA "qClip\logs"
Compress-Archive -Path $logDir -DestinationPath "$env:USERPROFILE\Desktop\qclip-smoke-win-logs.zip" -Force
```

### Windows pass checklist

- [ ] Installed without Docker  
- [ ] SmartScreen handled (More info → Run anyway)  
- [ ] Splash → UI  
- [ ] License activated  
- [ ] Short job completed  
- [ ] Clip plays  
- [ ] Logs folder present  

---

## Part 2 — macOS (Apple Silicon)

### What you need

- Mac with **Apple Silicon** (M1/M2/M3/…)
- macOS 12+
- ~16 GB RAM (32 GB better)
- License key from invite email (`SCPRO-…`)
- Installer: `qClip-mac-arm64.dmg`  
  - If your kit already has it under `installers/` → use that  
  - If not yet in the kit → someone with a Mac builds it (see “Build the DMG” below)

### Steps (when you have the DMG)

1. **Get the DMG**  
   Invite kit → `installers/qClip-mac-arm64.dmg` (or Drive / LS link).

2. **Open the DMG**  
   Double-click in Finder.

3. **Install**  
   Drag **qClip** into **Applications**.

4. **If Gatekeeper blocks** (“can’t be opened because…”)  
   - Finder → **Applications** → **qClip**  
   - **Right-click** (or Control-click) → **Open**  
   - Confirm **Open**  
   Unsigned beta only; notarization comes later.

5. **Launch**  
   Open **qClip** from Applications.  
   Splash → main UI (first run may download models).

6. **Confirm ready**  
   **Settings → Get started** → **Ready**.

7. **Activate license**  
   **Settings → License** → paste `SCPRO-…` → **Activate**.

8. **First clip (smoke)**  
   Same as Windows: short public URL → job **done** → play a clip.

9. **Confirm logs exist**

   ```
   ~/Library/Application Support/qClip/logs/
   ```

   Expect `sidecar.log` and `electron.log`.

### Zip logs for support

```bash
LOGDIR="$HOME/Library/Application Support/qClip/logs"
zip -r ~/Desktop/qclip-smoke-mac-logs.zip "$LOGDIR"
```

### macOS pass checklist

- [ ] Installed without Docker  
- [ ] Gatekeeper handled (right-click → Open)  
- [ ] Splash → UI  
- [ ] License activated  
- [ ] Short job completed  
- [ ] Clip plays  
- [ ] Logs folder present  

### Build the DMG (only if missing from the kit)

On an Apple Silicon Mac with Node 20+, Python 3.11+, Xcode CLT, ~15 GB free:

```bash
cd /path/to/streamclip   # branch cursor/desktop-first-completion-39d9 or master
./scripts/build_macos_solo.sh
# → apps/desktop/release/qClip-mac-arm64.dmg
./scripts/run_macos_solo_smoke.sh
```

Then copy the DMG into the invite kit `installers/` folder before distributing to Mac testers.

---

## What not to do

- Do **not** install Docker Desktop just to try the beta creator path  
- Do **not** use anonymous GitHub release download URLs (404)  
- Do **not** start long VODs for the first smoke — use a short clip  

## Help

- In-app: header **Help** → Troubleshooting / Report a bug  
- Docs: [Get qClip](BETA_DOWNLOAD.md) · [Quickstart](BETA_TESTER_QUICKSTART.md) · [Smoke checklist](HUMAN_DESKTOP_SMOKE.md) · [Solo gate](DESKTOP_SOLO_GATE.md)
