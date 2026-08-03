# Install qClip (operator notes)

> **Creators:** use the public page — [Download & how to use](index.md) (henna home). This file is **not published**.

> **Current Windows build:** `1.0.0-beta.20` · [**Download Setup**](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe) (~393 MB, unsigned)  
> **Mac (Apple Silicon interim):** [qClip-mac-arm64.dmg on v1.0.0-beta.6](https://github.com/WheresWellium/StreamClip/releases/download/v1.0.0-beta.6/qClip-mac-arm64.dmg) · not on Latest yet (Windows is `beta.12`)

Pick your platform. When install is done, continue to **[Create your first clip →](BETA_TESTER_QUICKSTART.md)**.

---

## Windows (recommended) {#one-click-installers}

**Call to action:** [Download qClip-Setup-win-x64.exe](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe)

1. **Download** the installer (no GitHub account).
2. **Run** it. If Windows shows *Windows protected your PC* → **More info → Run anyway** (unsigned beta — normal).
3. Open **qClip** from the Start menu.
4. Paste your invite key in **Settings → License** (`SCPRO-XXXX-XXXX-XXXX-XXXX`) → **Activate**.

No Docker. No terminal. No zip file.

**First run:** speech models download once (~1.5 GB, `medium`). Keep the app open — progress shows on the loading screen.

| | Requirement |
|-|-------------|
| OS | Windows 10/11 64-bit |
| RAM | 16 GB min (32 GB recommended) |
| Disk | 10 GB+ free (20 GB recommended) |
| GPU | Optional — CPU works, slower |

!!! tip "Upgrading from beta.7 or earlier?"
    Install beta.8, then **re-paste your license key once** if activation fails. beta.8 adds writable-dir fail-fast, model-download Retry, clearer boot failure pages, and honest local-only bug-report toasts. Report issues via the [GitHub beta bug template](https://github.com/WheresWellium/StreamClip/issues/new?template=beta-bug.yml).

!!! warning "White screen / many blank tray icons?"
    That was a Program Files write crash in older builds. **Task Manager → end all `qClip` processes**, uninstall, then reinstall from the link above (beta.8). You should see one tray icon and a dark splash (or a clear startup error), not a blank window.

**Next:** [Create your first clip →](BETA_TESTER_QUICKSTART.md)

---

## macOS {#macos}

**Call to action (Apple Silicon interim):** [Download qClip-mac-arm64.dmg (v1.0.0-beta.6)](https://github.com/WheresWellium/StreamClip/releases/download/v1.0.0-beta.6/qClip-mac-arm64.dmg)

A **universal** (Apple Silicon + Intel) DMG is next — rebuild with `./scripts/build_desktop_installer_macos.sh`, then upload `qClip-mac-universal.dmg`.

1. **Download** the `.dmg`.
2. Open the disk image → drag **qClip** to **Applications**.
3. First open: right-click → **Open** (or System Settings → Privacy & Security → **Open Anyway**) — unsigned beta, not notarized yet.
4. Paste your invite key in **Settings → License** (`SCPRO-…`) → **Activate**.

No Docker. No terminal for the normal path.

**First run:** speech models download once (~1.5 GB). Keep the app open. Encode is **CPU-only** on Mac desktop today — prefer a short public source for beta feedback.

| | Requirement |
|-|-------------|
| Chip | Apple Silicon (arm64) today; Intel via universal DMG when published |
| OS | macOS 12+ |
| RAM | 16 GB min (32 GB recommended) |
| Disk | 10 GB+ free (20 GB recommended) |

**Next:** [Create your first clip →](BETA_TESTER_QUICKSTART.md)

### Docker fallback (operators) {#macos-docker-no-public-dmg-yet}

Need Postgres workers, an Intel Mac, or the compose stack? Use [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/) + project files from your operator:

1. Launch Docker Desktop — wait until the menu-bar whale shows **running**.
2. In the project folder:

   ```bash
   cp .env.example .env
   docker compose up -d
   ```

3. Open [http://localhost:3000](http://localhost:3000)
4. Import your key once, then activate in **Settings → License**:

   ```bash
   docker compose exec -e PYTHONPATH=/app api python scripts/import_invite_license.py \
     --key SCPRO-XXXX-XXXX-XXXX-XXXX --tier admin --email you@example.com
   ```

---

## Operators — Windows Docker / GPU {#advanced-docker-self-host-operators}

Prefer Postgres + GPU workers instead of the `.exe`? Same compose path as Mac Docker after cloning the repo. Use `.\scripts\start_local.ps1` on Windows when available. Cohort keys still need `import_invite_license.py` before UI activate.

Creators on Windows should use the **installer** above — not this path.

---

## Install problems?

| Symptom | Fix |
|---------|-----|
| SmartScreen (Windows) | **More info → Run anyway** |
| Gatekeeper (Mac) | Right-click → **Open**, or Privacy & Security → **Open Anyway** |
| Key rejected | Paste full key with dashes; on Docker, run the import command first |
| Stuck on first launch | Wait for the ~1.5 GB model download |
| Very slow clips | Expected on CPU (Mac desktop / no GPU) — try a ~15 min source |

More answers: [FAQ](BETA_FAQ.md) · [Troubleshooting](tutorials/TUTORIAL_TROUBLESHOOTING.md)
