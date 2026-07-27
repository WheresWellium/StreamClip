# Get qClip — Beta Access


> **Current Windows installer:** `1.0.0-beta.4` (2026-07-24) — [download Setup exe](https://github.com/WheresWellium/StreamClip/releases/latest/download/StreamClip-Setup-win-x64.exe)
> *(Next publish ships as `qClip-Setup-win-x64.exe`; beta.4 artifact name remains StreamClip until republished.)*


**qClip** turns long videos into short vertical clips — on **your computer**, not in the cloud.

**New here?** Read this page top to bottom, or jump to the [15-minute quickstart](BETA_TESTER_QUICKSTART.md).

---

## Choose how you want to run it

| Option | Who it's for | Difficulty |
|--------|--------------|------------|
| **Docker on Windows or Mac** | Most beta testers (recommended) | Medium — install Docker once, then one command to start |
| **Windows installer (.exe)** | People who do not want Docker | Easy — download and install like any app |

Both options are free. You do **not** need a GitHub account.

---

## What's available right now

| Path | Status | Who it's for |
|------|--------|--------------|
| **Docker self-host (Windows)** | ✅ Ready | Beta testers with Docker Desktop |
| **Docker self-host (macOS)** | ✅ Ready | Beta testers on Apple Silicon or Intel Mac |
| **Windows one-click installer (.exe)** | ✅ Ready (unsigned beta) | Creators who want no Docker — SmartScreen may warn |
| **macOS one-click installer (.dmg)** | 🔜 Coming soon | General creators — scaffold in progress |

**Phase 0 testers:** Docker is still the most complete path. The Windows `.exe` works well for quick trials without Docker.

---

## Windows installer (no Docker)

If you prefer **not** to install Docker:

1. Download **[StreamClip-Setup-win-x64.exe](https://github.com/WheresWellium/StreamClip/releases/latest/download/StreamClip-Setup-win-x64.exe)** (about 390 MB)
2. Run the installer

**If Windows shows "Windows protected your PC"**

This is normal for an unsigned beta build. It does **not** mean the file is a virus.

1. Click **More info**
2. Click **Run anyway**
3. Finish install and open StreamClip from the Start menu
4. Sign up or log in, then paste your license key in **Settings → License**

The desktop app runs everything locally. You still need your **license key** from your invite email.

---

## Docker install (Windows and Mac)

Pick your platform below.

---

## Choose your platform

=== "Windows"

    ### Requirements

    - **Windows 10 or 11** (64-bit)
    - **Docker Desktop** — [download](https://www.docker.com/products/docker-desktop/) (WSL2 backend)
    - **16 GB RAM** minimum (32 GB recommended)
    - **NVIDIA GPU** strongly recommended — CPU-only works but is much slower

    ### Step 1 — Get the beta package

    You should have received a `.zip` or a private repo link in your invite email. If you haven't:

    - Check spam for an email from Wellium
    - Reply to your invite email and ask for the download link

    ### Step 2 — Extract and set up

    ```powershell
    # Extract the beta zip to a folder, then:
    cd streamclip
    Copy-Item .env.example .env
    ```

    ### Step 3 — Start StreamClip

    ```powershell
    docker compose up -d
    ```

    First run downloads Docker images — allow 5–10 minutes on a fast connection.

    ### Step 4 — Verify it's running

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

    ### Step 2 — Get the beta package

    Same as Windows: `.zip` or private repo link from your invite email.

    ```bash
    # ZIP: unzip, then:
    cd ~/Downloads/streamclip   # or wherever you extracted

    # Or clone if your invite included a repo URL:
    # git clone <LINK_FROM_INVITE> streamclip && cd streamclip
    ```

    ### Step 3 — Configure

    ```bash
    cp .env.example .env
    ```

    Defaults work for local beta — no API keys required to start.

    ### Step 4 — Start StreamClip

    ```bash
    docker compose up -d
    ```

    First run downloads images (~2–5 GB). Allow 5–15 minutes. Later starts take about a minute.

    ### Step 5 — Verify it's running

    PowerShell verify script is optional on Mac. Use these checks:

    ```bash
    docker compose ps
    curl -s http://localhost:8000/api/health
    open http://localhost:3000
    ```

    You want containers **healthy** / **running**, health JSON with an OK-style status, and the StreamClip UI in the browser.

    Optional (if you installed [PowerShell Core](https://github.com/PowerShell/PowerShell)):

    ```bash
    pwsh -File ./scripts/verify_stack.ps1
    ```

---

## After install (Windows and Mac)

### Activate your license

1. Open the app at [http://localhost:3000](http://localhost:3000)
2. Sign up / log in
3. Go to **Settings → License**
4. Paste the license key from your invite email
5. Confirm — beta keys unlock **full access**

### Create your first clip

1. Click **New job**
2. Paste any **public** video URL — Twitch VOD, YouTube, Kick, or a direct `.mp4` link
3. Submit and watch the progress bar
4. When status shows **done**, review and approve clips you like

**Speed guide**

| Setup | ~1-hour VOD |
|-------|-------------|
| Windows + NVIDIA GPU | ~20–25 minutes |
| Windows / Mac CPU-only | ~60–90+ minutes |

### Publish to YouTube Shorts (optional)

1. Open a finished, approved clip
2. **Settings → Distribution → Connect YouTube Shorts** → sign in with Google
3. Click **Publish** on any approved clip

!!! note "TikTok"
    TikTok direct publish is inbox-upload only during beta (awaiting app audit). Your clip will be saved to TikTok drafts — finish posting inside the TikTok app.

### Stop StreamClip

=== "Windows"

    ```powershell
    docker compose down
    ```

=== "macOS"

    ```bash
    docker compose down
    ```

Your data (jobs, clips, settings) stays in Docker volumes. Add `-v` only if you want to wipe everything.

---

## System requirements

| | Windows | macOS |
|-|---------|-------|
| OS | Windows 10/11 64-bit | macOS 12+ |
| Runtime | Docker Desktop (WSL2) | Docker Desktop for Mac |
| RAM | 16 GB min / 32 GB recommended | Same |
| Disk | 10 GB+ free (20 GB SSD better) | 20 GB+ free recommended |
| GPU | NVIDIA + NVENC recommended | CPU only (no NVENC) |
| Accounts | None to install | None to install |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| App won't load at localhost:3000 | Wait 60 s after `docker compose up -d`; run `docker compose ps` — all services should be up |
| `docker compose` not found | Install/update Docker Desktop and ensure it is **running** |
| Mac: Docker is slow / fans loud | Give Docker more CPUs/RAM (Docker Desktop → Settings → Resources). Prefer Apple Silicon build on M-series |
| Very slow clips on Windows | Enable GPU in Docker Desktop → Settings → Resources → GPU |
| Very slow clips on Mac | Expected without NVIDIA — use shorter source videos for beta |
| License key not accepted | Paste the full key including dashes; under **Settings → License**, use **Show details** on **This install** if support asks |
| Windows: `verify_stack.ps1` fails | Post the full output in the beta channel — include GPU model |
| Mac: `curl` health fails | Confirm API container is running: `docker compose logs api --tail 50` |

---

## Get help

Use **Report a bug** or **Beta feedback** in the app header — every submission is read even if auto-reply isn't set up yet. Or reply directly to your invite email.

---

## One-click installers

| Platform | Artifact | Status |
|----------|----------|--------|
| Windows | [`StreamClip-Setup-win-x64.exe`](https://github.com/WheresWellium/StreamClip/releases/latest/download/StreamClip-Setup-win-x64.exe) | ✅ **v1.0.0-beta.2** published — unsigned; SmartScreen may warn → More info → Run anyway |
| macOS | `StreamClip-mac-arm64.dmg` | 🔜 Scaffold ready; needs a Mac host to produce the DMG |

**Release page:** [v1.0.0-beta.2](https://github.com/WheresWellium/StreamClip/releases/tag/v1.0.0-beta.2)

Docker remains the primary Phase 0 path (full stack verify). Use the `.exe` for desktop / no-Docker trials.

### For friends helping build the macOS `.dmg` (not required for beta use)

See **[macOS installer — builder notes](MACOS_INSTALLER.md)**. End users should **not** need that path yet — use Docker above.

---

*qClip · Phase 0 creator beta · [Known issues](BETA_KNOWN_ISSUES.md) · [Full quickstart](BETA_TESTER_QUICKSTART.md)*
