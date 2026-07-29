# Install qClip

> **Current Windows build:** `1.0.0-beta.6` · [**Download Setup**](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe) (~393 MB)

Pick your platform. When install is done, continue to **[Create your first clip →](BETA_TESTER_QUICKSTART.md)**.

---

<a id="one-click-installers"></a>

## Windows (recommended)

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

!!! tip "Upgrading from beta.5 or earlier?"
    Install beta.6, then **re-paste your license key once**. That refreshes install secrets and the Link-jobs fix.

**Next:** [Create your first clip →](BETA_TESTER_QUICKSTART.md)

---

## macOS (Docker — no public .dmg yet)

There is no one-click `.dmg` on GitHub yet. Mac beta uses **Docker Desktop** on your machine (CPU-only encode — expect longer jobs; try a short source first).

**Call to action:** Install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/), then get the project files from your operator (reply to your invite if you need a link).

1. Install and launch Docker Desktop — wait until the menu-bar whale shows **running**.
2. Open a terminal in the project folder:

   ```bash
   cp .env.example .env
   docker compose up -d
   ```

   First pull is ~2–5 GB (5–15 minutes).

3. Open [http://localhost:3000](http://localhost:3000)
4. Import your key once (Docker DB starts empty):

   ```bash
   docker compose exec -e PYTHONPATH=/app api python scripts/import_invite_license.py \
     --key SCPRO-XXXX-XXXX-XXXX-XXXX --tier admin --email you@example.com
   ```

5. In the app: **Settings → License** → paste the **same** key → **Activate**.

Stop later with `docker compose down` (data stays in volumes).

**Next:** [Create your first clip →](BETA_TESTER_QUICKSTART.md)

---

<a id="advanced-docker-self-host-operators"></a>

## Operators — Windows Docker / GPU

Prefer Postgres + GPU workers instead of the `.exe`? Same compose path as Mac after cloning the repo. Use `.\scripts\start_local.ps1` on Windows when available. Cohort keys still need `import_invite_license.py` before UI activate.

Creators on Windows should use the **installer** above — not this path.

---

## Install problems?

| Symptom | Fix |
|---------|-----|
| SmartScreen warning | **More info → Run anyway** |
| Key rejected | Paste full key with dashes; on Docker, run the import command first |
| Stuck on first launch | Wait for the ~1.5 GB model download |
| Very slow clips | Expected on CPU — try a ~15 min source |

More answers: [FAQ](BETA_FAQ.md) · [Troubleshooting](tutorials/TUTORIAL_TROUBLESHOOTING.md)
