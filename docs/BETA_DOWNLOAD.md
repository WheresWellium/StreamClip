# Get qClip — Beta Access

> **Current Windows installer:** `1.0.0-beta.6` (2026-07-28) — [**Download qClip-Setup-win-x64.exe**](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe) (about 393 MB)

**qClip** is the all-in-one clip studio on **your computer** — paste a URL or upload, reframe to any aspect ratio, and rank what to ship first.

---

<a id="one-click-installers"></a>

## Download and run (Windows)

**[Download qClip for Windows](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe)**

Three steps:

1. **Download** the installer above (no GitHub account required).
2. **Run** it and open qClip from the Start menu.
3. **Paste your license key** in **Settings → License** (from your invite email).

You do **not** need to sign up, log in, or install Docker for the Windows installer path.

**If Windows shows "Windows protected your PC"**

This is normal for an unsigned beta build. It does **not** mean the file is a virus.

1. Click **More info**
2. Click **Run anyway**
3. Finish install and open qClip

**First run:** qClip downloads speech models on first use (~1.5 GB for the beta `medium` model). Keep the app open — progress appears on the loading screen.

**New here?** See the [15-minute quickstart](BETA_TESTER_QUICKSTART.md).

---

## After install

### Create your first clip

1. Click **New job**
2. Paste any **public** video URL — Twitch VOD, YouTube, Kick, or a direct `.mp4` link — or upload a file
3. Submit and watch the progress bar
4. When status shows **done**, review and approve clips you like

**Speed guide (CPU-only desktop bundle)**

| Source length | Typical time |
|---------------|--------------|
| ~15-minute clip | ~10–20 minutes |
| ~1-hour VOD | ~60–90+ minutes |

### Publish to YouTube Shorts (optional)

1. Open a finished, approved clip
2. **Settings → Distribution → Connect YouTube Shorts** → sign in with Google
3. Click **Publish** on any approved clip

!!! note "TikTok"
    TikTok direct publish is inbox-upload only during beta (awaiting app audit). Your clip will be saved to TikTok drafts — finish posting inside the TikTok app.

### Get help

Use **Report a bug** or **Beta feedback** in the app header — every submission is read even if auto-reply isn't set up yet. Or reply directly to your invite email.

---

## System requirements (Windows installer)

| | Requirement |
|-|-------------|
| OS | Windows 10/11 64-bit |
| RAM | 16 GB minimum (32 GB recommended) |
| Disk | 10 GB+ free (20 GB SSD recommended — includes first-run models) |
| GPU | Not required for the desktop bundle (CPU encode; slower than GPU Docker hosts) |
| Accounts | None to install or clip |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Windows SmartScreen warning | Click **More info → Run anyway** (unsigned beta) |
| License key not accepted | Paste the full key including dashes; open **Settings → License → Show details** on **This install** if support asks |
| App stuck on first launch | First run downloads ~1.5 GB of speech models — wait for the progress indicator |
| Clips very slow | Expected on CPU-only desktop — try a shorter source video for beta |
| Upgraded from an older beta build | Re-paste your license key once in **Settings → License** |

---

## What's coming

| Platform | Status |
|----------|--------|
| Windows `.exe` | ✅ **v1.0.0-beta.6** — [Latest release](https://github.com/WheresWellium/StreamClip/releases/latest) |
| macOS `.dmg` | 🔜 Coming soon — scaffold in progress |

---

## Advanced: Docker self-host (operators)

The sections below are for **operators and developers** who prefer the full Docker stack (Postgres, GPU workers, stack verify). Phase 0 testers on Windows should use the **installer above** — no zip extract, no terminal commands.

### Choose your platform

=== "Windows"

    ### Requirements

    - **Windows 10 or 11** (64-bit)
    - **Docker Desktop** — [download](https://www.docker.com/products/docker-desktop/) (WSL2 backend)
    - **16 GB RAM** minimum (32 GB recommended)
    - **NVIDIA GPU** strongly recommended — CPU-only works but is much slower

    ### Step 1 — Get the repo

    Clone or download the repo (private link from your operator). If you only have an invite email with a license key, use the Windows installer instead.

    ```powershell
    cd streamclip
    Copy-Item .env.example .env
    ```

    ### Step 2 — Start qClip

    ```powershell
    docker compose up -d
    ```

    First run downloads Docker images — allow 5–10 minutes on a fast connection.

    ### Step 3 — Verify it's running

    ```powershell
    .\scripts\verify_stack.ps1
    ```

    This should exit with **all checks green**. If not, do not create jobs yet — post your output in the beta channel from your invite email.

    Or open:

    - **App:** [http://localhost:3000](http://localhost:3000)
    - **API health:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

=== "macOS"

    ### Requirements

    - **macOS 12+** (Apple Silicon M1/M2/M3/M4 preferred; Intel Mac works)
    - **Docker Desktop for Mac** — [download](https://www.docker.com/products/docker-desktop/) (pick **Apple Silicon** or **Intel** to match your Mac)
    - **16 GB RAM** minimum (32 GB recommended)
    - **~20 GB free disk** for images + first-run models
    - **No NVIDIA GPU on Mac** — clips run on CPU (slower). That is expected and supported.

    **You do not need:** an Apple Developer account, Xcode (full app), Node, Python, or a paid Mac App Store anything — only Docker Desktop.

    ### Step 1 — Install Docker Desktop

    1. Download Docker Desktop for Mac from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
    2. Open the `.dmg`, drag **Docker** to Applications, launch it
    3. Complete first-run setup and wait until the menu-bar whale shows **Docker Desktop is running**
    4. (Apple Silicon) Prefer the **Apple Silicon** build — Rosetta-only Intel images are slower

    ### Step 2 — Get the repo

    ```bash
    cd ~/Downloads/streamclip   # or wherever you cloned
    cp .env.example .env
    ```

    ### Step 3 — Start qClip

    ```bash
    docker compose up -d
    ```

    First run downloads images (~2–5 GB). Allow 5–15 minutes. Later starts take about a minute.

    ### Step 4 — Verify it's running

    PowerShell verify script is optional on Mac. Use these checks:

    ```bash
    docker compose ps
    curl -s http://localhost:8000/api/health
    open http://localhost:3000
    ```

    You want containers **healthy** / **running**, health JSON with an OK-style status, and the qClip UI in the browser.

    Optional (if you installed [PowerShell Core](https://github.com/PowerShell/PowerShell)):

    ```bash
    pwsh -File ./scripts/verify_stack.ps1
    ```

### After Docker install

#### Activate your license

1. Open the app at [http://localhost:3000](http://localhost:3000)
2. Go to **Settings → License**
3. Paste the license key from your invite email
4. Confirm — beta keys unlock **full access**

Manual cohort keys on **beta.5** may require a one-time import — see the [quickstart](BETA_TESTER_QUICKSTART.md#step-2-activate-your-license-key). **beta.6+** seeds keys at install.

#### Stop qClip

=== "Windows"

    ```powershell
    docker compose down
    ```

=== "macOS"

    ```bash
    docker compose down
    ```

Your data (jobs, clips, settings) stays in Docker volumes. Add `-v` only if you want to wipe everything.

### Docker troubleshooting

| Problem | Fix |
|---------|-----|
| App won't load at localhost:3000 | Wait 60 s after `docker compose up -d`; run `docker compose ps` — all services should be up |
| `docker compose` not found | Install/update Docker Desktop and ensure it is **running** |
| Mac: Docker is slow / fans loud | Give Docker more CPUs/RAM (Docker Desktop → Settings → Resources). Prefer Apple Silicon build on M-series |
| Very slow clips on Windows | Enable GPU in Docker Desktop → Settings → Resources → GPU |
| Very slow clips on Mac | Expected without NVIDIA — use shorter source videos for beta |
| Windows: `verify_stack.ps1` fails | Post the full output in the beta channel — include GPU model |
| Mac: `curl` health fails | Confirm API container is running: `docker compose logs api --tail 50` |

### Docker system requirements

| | Windows | macOS |
|-|---------|-------|
| OS | Windows 10/11 64-bit | macOS 12+ |
| Runtime | Docker Desktop (WSL2) | Docker Desktop for Mac |
| RAM | 16 GB min / 32 GB recommended | Same |
| Disk | 10 GB+ free (20 GB SSD better) | 20 GB+ free recommended |
| GPU | NVIDIA + NVENC recommended | CPU only (no NVENC) |

### macOS `.dmg` builder notes

See **[macOS installer — builder notes](MACOS_INSTALLER.md)**. End users should use the Windows installer or Docker above.

---

*qClip · Phase 0 creator beta · [Known issues](BETA_KNOWN_ISSUES.md) · [Full quickstart](BETA_TESTER_QUICKSTART.md)*
