# qClip Beta — Quickstart Guide

Welcome to the qClip beta. This guide takes you from **zero to your first clip**. Most people finish setup in about **15 minutes**.

---

## The short version (Windows installer)

1. **[Download the installer](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe)** — or open [Get qClip](BETA_DOWNLOAD.md)
2. **Run** it (SmartScreen? → **More info → Run anyway**)
3. **Paste your license key** in **Settings → License**
4. Click **New job**, paste a **public video link** or upload a file, and wait for clips

You do **not** need a GitHub account, Docker, Python, or coding experience for the Windows installer.

**First run:** qClip downloads speech models (~1.5 GB). Keep the app open — you'll see progress on the loading screen.

**Help in the app:** Open **Help** from the header for install, GPU, and troubleshooting — without leaving qClip.

---

## Step 1 — Download and install (Windows)

1. Download **[qClip-Setup-win-x64.exe](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe)** (about 490 MB)
2. Run the installer
3. If Windows shows **"Windows protected your PC"**, click **More info → Run anyway** (unsigned beta — normal)
4. Open qClip from the Start menu

Full install notes: [Get qClip](BETA_DOWNLOAD.md)

---

## Step 2 — Activate your license key

1. Open **Settings → License**
2. Paste the license key from your invite email (format: `SCPRO-XXXX-XXXX-XXXX-XXXX`)
3. Click **Activate** — beta keys unlock **full access**

You do **not** need to sign up or log in first.

!!! tip "Upgraded from an older beta?"
    Re-paste your license key once in **Settings → License**.

---

## Step 3 — Confirm you're ready

1. Go to **Settings → Get started** (or finish **Onboarding** on first launch)
2. You should see **Ready** — you can create a job
3. If you see **Needs attention**, open **Help → Troubleshooting** before submitting URLs

---

## Step 4 — Your first clip

1. Click **New job** on the home screen
2. Paste any **public** video URL or upload a file:
   - Twitch VOD: `https://www.twitch.tv/videos/...`
   - YouTube video: `https://www.youtube.com/watch?v=...`
   - Kick stream: `https://kick.com/...`
   - Direct `.mp4` URL
3. Optionally set a title and click **Submit**
4. Watch the progress bar — processing happens in stages (download → transcribe → detect → render)
5. When status shows **done**, clip previews appear

**How long does it take? (CPU-only desktop bundle)**

| Source length | Typical time |
|---------------|--------------|
| ~15-minute clip | ~10–20 minutes |
| ~1-hour VOD | ~60–90+ minutes |

---

## Step 5 — Approve clips and publish

1. Open a finished clip → review the preview
2. Click **Approve** on clips you want to keep
3. To publish to **YouTube Shorts**:
   - Go to **Settings → Distribution → Connect YouTube Shorts**
   - Sign in with your Google account
   - Return to the clip and click **Publish**

!!! info "TikTok"
    TikTok direct publish is inbox-only during beta (waiting on app audit). Your clip will be saved to TikTok drafts — complete the post inside the TikTok app.

!!! tip "Scheduled publishes"
    Desktop installer: scheduled posts only fire while the app is running — see [Known issues](BETA_KNOWN_ISSUES.md).

---

## Before you start (reference)

**You need (Windows installer):**

- **Windows 10/11** (64-bit)
- 16 GB RAM minimum — 32 GB recommended
- 10 GB+ free disk (20 GB recommended — includes first-run models)
- Your license key from your invite email

**Simple words**

| Term | What it means |
|------|----------------|
| License key | Unlock code from your invite email |
| Job | One video you are processing |
| Clip | One short video cut from that job |

**You do not need:**

- A GitHub account
- Docker Desktop
- Python or Node.js
- To extract a zip file (installer path)
- To understand programming or the command line

---

## Advanced: Docker self-host (operators)

Use this path only if an operator gave you repo access and you want the full Docker stack (Postgres, GPU workers, stack verify). **Phase 0 testers on Windows should use the installer above.**

### Two ways to run qClip

| Way | Best for | Notes |
|-----|----------|-------|
| **Windows installer (.exe)** | Most beta testers | Steps above — no Docker |
| **Docker** | Operators / GPU hosts | Windows and Mac; steps below |

### Docker — before you start

**You need:**

- **Windows 10/11** or **macOS 12+** (Apple Silicon preferred on Mac)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running (free)
- 16 GB RAM minimum — 32 GB recommended
- On Windows: NVIDIA GPU recommended (CPU-only works but is much slower)
- On Mac: CPU-only is expected (no NVIDIA / NVENC) — allow longer job times
- Repo clone or zip from your operator (not required for `.exe` users)

### Docker — Step 1: Install Docker Desktop

=== "Windows"

    1. Download it free at [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
    2. Install and open Docker Desktop
    3. Complete the first-run setup (enable WSL 2 if prompted — recommended)
    4. Wait until the Docker whale icon in the taskbar shows **"Docker Desktop is running"**

=== "macOS"

    1. Download **Docker Desktop for Mac** — choose **Apple Silicon** or **Intel** to match your machine
    2. Open the `.dmg`, drag Docker to Applications, launch it
    3. Complete first-run setup
    4. Wait until the menu-bar whale shows **Docker Desktop is running**

### Docker — Step 2: Get the qClip files

Clone or download the repo from your operator:

=== "Windows"

    ```powershell
    git clone <LINK_FROM_OPERATOR> streamclip
    cd streamclip
    Copy-Item .env.example .env
    ```

=== "macOS"

    ```bash
    git clone <LINK_FROM_OPERATOR> streamclip
    cd streamclip
    cp .env.example .env
    ```

### Docker — Step 3: Start qClip (one command)

=== "Windows"

    ```powershell
    .\scripts\start_local.ps1
    ```

    Phase 0 alias (same script): `.\scripts\start.ps1` — thin wrapper around `start_local.ps1`.

    This creates `.env` from `.env.example` if needed, starts Docker, runs migrations, and calls `verify_stack.ps1` automatically.

=== "macOS"

    Manual equivalent (Docker does not ship PowerShell by default):

    ```bash
    cp .env.example .env    # skip if .env exists
    docker compose up -d --build
    docker compose exec -T api alembic upgrade head
    ```

    Or, if [PowerShell Core](https://github.com/PowerShell/PowerShell) is installed:

    ```bash
    pwsh -File ./scripts/start_local.ps1
    ```

The defaults work for local beta — **no API keys or account required** to start.

The first time you run this, Docker downloads images (~2–5 GB). Allow 5–10 minutes on a good connection (Mac may take a bit longer). After that, starts take about 30–60 seconds.

!!! tip "Step-by-step install"
    See the [Install tutorial](tutorials/TUTORIAL_INSTALL.md) for numbered steps and platform notes.

### Docker — Step 4: Confirm everything is running

**In the app:**

1. Open [http://localhost:3000](http://localhost:3000)
2. Go to **Settings → Get started** (or finish **Onboarding** on first launch)
3. You should see **Ready** — you can create a job. If you see **Needs attention**, open **Help → Troubleshooting** before submitting URLs.

**Optional deeper check:**

=== "Windows"

    `start_local.ps1` / `start.ps1` already runs the full verify on start. For a **fast second-terminal smoke** (ports + health endpoints; **no pytest**):

    ```powershell
    .\scripts\health.ps1
    ```

    Full gate (unit suite + stack — use this when something looks wrong or before trusting a clean install):

    ```powershell
    .\scripts\verify_stack.ps1
    ```

    All checks should be green. If any fail, **stop here** and use **Report a bug** in the app header (or reply to your invite email) with the script output before creating jobs.

=== "macOS"

    ```bash
    docker compose ps
    curl -s http://localhost:8000/api/health
    open http://localhost:3000
    ```

    Containers should be running/healthy and the health endpoint should respond. Optional: `pwsh -File ./scripts/verify_stack.ps1` if PowerShell Core is installed.

!!! note "API health URL (operators only)"
    `http://localhost:8000/api/health` is for Docker debugging — not shown in the beta app. Desktop `.exe` users can skip it; use **Get started** in Settings instead.

### Docker — Step 5: Activate your license key

Manual cohort keys (`SCPRO-…` from the invite email) must exist in **your** local Postgres before the UI can activate them.

**Docker self-host (once per machine), from the repo root with the stack up:**

```powershell
docker compose exec -e PYTHONPATH=/app api python scripts/import_invite_license.py `
  --key SCPRO-XXXX-XXXX-XXXX-XXXX --tier admin --email you@example.com
```

Then:

1. Go to **Settings → License**
2. Paste the **same** license key from your invite email (format: `SCPRO-…` with dashes)
3. Click **Activate** — a confirmation shows your features are unlocked

Lemon Squeezy checkout keys can skip the import step (first activate needs network). Your beta key gives **full access** — no paywalls.

### Docker — Step 6: Stop qClip when done

```bash
docker compose down
```

Your jobs, clips, and settings are saved in Docker volumes and will be there next time you start. To fully wipe and start fresh, add `-v` (this deletes everything).

---

## Frequently Asked Questions

**Do I need a GitHub account to use qClip?**
No. Download the Windows installer from [Get qClip](BETA_DOWNLOAD.md) and paste your license key. No GitHub login required.

**Do I need Docker?**
No — not for the Windows installer. Docker is an optional operator path for GPU hosts and stack verify.

**My license key isn't working. What format should it be?**
The key from your beta invite starts with `SCPRO-` (four hex groups with dashes). Paste the entire string. If it still fails, open **Settings → License**, click **Show details** under **This install**, and reply to your invite email with what you see.

**What features does my beta key unlock?**
Everything — full access, no limits. Your beta key is equivalent to the highest tier.

**Does qClip send my videos to the cloud?**
No. All processing happens on your machine. Your videos never leave unless you publish to YouTube/TikTok through the publish flow.

**Can I run qClip on a Mac?**
The one-click `.dmg` is not ready yet. Mac is supported via **Docker self-host** — see the advanced section above or [Get qClip](BETA_DOWNLOAD.md#advanced-docker-self-host-operators).

**The app is running but clips are taking way too long. Help?**
On the **Windows installer**, the beta bundle is CPU-only — try a shorter source video. On **Docker + Windows**, enable GPU in Docker Desktop → Settings → Resources → GPU, then `docker compose exec worker nvidia-smi`. On **Mac Docker**: slow jobs are normal without NVIDIA.

**TikTok says "upload to inbox" instead of publishing directly. Is that a bug?**
No — this is expected during beta. TikTok restricts direct publish until an app audit is complete. Your clip will be in TikTok drafts; post it from within the TikTok app.

**How do I update qClip when a new beta version ships?**
You'll get an email. **Windows installer:** download and run the new `.exe`. **Docker:** pull and restart:
```bash
docker compose pull
docker compose up -d
```

**Where do I report bugs or feedback?**
Use **Report a bug** or **Beta feedback** in the app header (top bar). Every submission is logged and read. You can also reply to your invite email.

**What information should I include in a bug report?**
- The job ID (shown on the job detail page)
- Your GPU model (or "no GPU / CPU only")
- What you expected vs. what happened
- Docker hosts: last 50 lines of logs — `docker compose logs api worker --tail 50`

---

## Cheat sheet

| Task | Command / Location |
|------|--------------------|
| Download (Windows) | [qClip-Setup-win-x64.exe](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe) |
| Activate license | **Settings → License** |
| Check health (Windows `.exe`) | **Settings → Get started** — should show **Ready** |
| Start qClip (Docker, Windows) | `.\scripts\start_local.ps1` (alias: `.\scripts\start.ps1`) |
| Start qClip (Docker, Mac) | `docker compose up -d` |
| Stop qClip (Docker) | `docker compose down` |
| Check health (Docker) | **Settings → Get started** or `.\scripts\health.ps1` / `.\scripts\verify_stack.ps1` |
| In-app Help | Header → **Help** |
| Settings → Distribution | Connect YouTube Shorts / TikTok |

---

*Phase 0 beta · [Get qClip](BETA_DOWNLOAD.md) · [Known issues](BETA_KNOWN_ISSUES.md) · [Full test plan](BETA_TESTER_PLAN.md) · Questions? Reply to your invite email.*
