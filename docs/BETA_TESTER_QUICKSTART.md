# qClip Beta — Quickstart Guide

Welcome to the qClip beta. This guide takes you from **zero to your first short clip**. Most people finish setup in about **15 minutes**.

---

## The short version

1. Install **Docker Desktop** (free) and make sure it is running
2. Open the qClip folder from your invite and run **one start command**
3. Open **http://localhost:3000** in your browser
4. Paste a **public video link** and wait for clips to appear
5. Paste your **license key** in **Settings → License** (from your invite email)

**Two ways to run qClip**

| Way | Best for | Notes |
|-----|----------|-------|
| **Docker** (recommended) | Windows and Mac testers | Full features; steps below |
| **Windows installer (.exe)** | No Docker | [Download the installer](BETA_DOWNLOAD.md#one-click-installers) — Windows may show a security warning; click **More info → Run anyway** |

You do **not** need a GitHub account, Python, or coding experience for either path.

**Help in the app:** Open **Help** from the header for quickstart, install, GPU, and troubleshooting — without leaving qClip. The shipped app does **not** include OpenAPI/Swagger or operator settings; those are for local development only.

---

## Before you start

**You need:**

- **Windows 10/11** or **macOS 12+** (Apple Silicon preferred on Mac)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running (free)
- 16 GB RAM minimum — 32 GB recommended
- On Windows: NVIDIA GPU recommended (CPU-only works but is much slower)
- On Mac: CPU-only is expected (no NVIDIA / NVENC) — allow longer job times
- The beta package (`.zip`) or private repo link from your invite email
- Your license key from the same invite email (looks like `SCPRO-XXXX-XXXX-XXXX-XXXX`)

**Simple words**

| Term | What it means |
|------|----------------|
| Docker | Free app that runs qClip locally |
| License key | Unlock code from your invite email |
| Job | One video you are processing |
| Clip | One short video cut from that job |

**You do not need:**

- A GitHub account
- Python or Node.js installed
- An Apple Developer account (Mac)
- Any cloud subscription
- To understand programming or the command line (copy/paste the commands we give you)

---

## Step 1 — Install Docker Desktop

If Docker Desktop is not already installed:

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

---

## Step 2 — Get the qClip files

**Option A — ZIP download (easiest)**

Extract the beta `.zip` from your invite email to any folder (e.g. `C:\qClip` or `~/qClip`).

**Option B — Private repo link**

If your invite included a private repo link, you'll need Git installed:

=== "Windows"

    ```powershell
    git clone <LINK_FROM_INVITE_EMAIL> streamclip
    ```

=== "macOS"

    ```bash
    git clone <LINK_FROM_INVITE_EMAIL> streamclip
    ```

Replace `<LINK_FROM_INVITE_EMAIL>` with the exact URL from your email. If you're unsure which option you have, reply to your invite email.

---

## Step 3 — Start qClip (one command)

`cd` into your qClip folder, then run the **primary install script**:

=== "Windows"

    ```powershell
    .\scripts\start_local.ps1
    ```

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

---

## Step 4 — Confirm everything is running

**In the app (all installs):**

1. Open [http://localhost:3000](http://localhost:3000)
2. Go to **Settings → Get started** (or finish **Onboarding** on first launch)
3. You should see **Ready** — you can create a job. If you see **Needs attention**, open **Help → Troubleshooting** before submitting URLs.

**Docker beta only (optional deeper check):**

=== "Windows"

    `start_local.ps1` already runs verify. To re-check:

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

You can also confirm in the browser:

- **App:** [http://localhost:3000](http://localhost:3000) — qClip home screen

!!! note "API health URL (operators only)"
    `http://localhost:8000/api/health` is for Docker debugging — not shown in the beta app. Desktop `.exe` users can skip it; use **Get started** in Settings instead.

---

## Step 5 — Account (optional)

1. Open [http://localhost:3000](http://localhost:3000)
2. **Sign up** is optional for local Phase 0 testing — the stack works without an account for pipeline flows
3. Create an account when you want persisted settings, vault ownership, or distribution OAuth tied to a user

!!! tip "Forgot your password?"
    Use the **Forgot password?** link on the login page. A reset link will be sent to your email if SMTP is configured by the operator. For local installs, your operator can reset it manually.

---

## Step 6 — Activate your license key (optional)

1. Go to **Settings → License**
2. Paste the license key from your invite email (format: `SCPRO-…` with dashes)
3. Click **Activate** — a confirmation shows your features are unlocked

Your beta key gives you **full access to every feature** — no paywalls, no feature gates. Skip this step if your invite is for technical pipeline testing only (T0-1 … T0-4).

---

## Step 7 — Your first clip

1. Click **New job** on the home screen
2. Paste any **public** video URL:
   - Twitch VOD: `https://www.twitch.tv/videos/...`
   - YouTube video: `https://www.youtube.com/watch?v=...`
   - Kick stream: `https://kick.com/...`
   - Direct `.mp4` URL
3. Optionally set a title and click **Submit**
4. Watch the progress bar — processing happens in stages (download → transcribe → detect → render)
5. When status shows **done**, clip previews appear

**How long does it take?**

| Setup | 1-hour VOD |
|-------|-----------|
| Windows + NVIDIA GPU | ~20–25 minutes |
| Windows / Mac CPU only | ~60–90+ minutes |

---

## Step 8 — Approve clips and publish

1. Open a finished clip → review the preview
2. Click **Approve** on clips you want to keep
3. To publish to **YouTube Shorts**:
   - Go to **Settings → Distribution → Connect YouTube Shorts**
   - Sign in with your Google account
   - Return to the clip and click **Publish**

!!! info "TikTok"
    TikTok direct publish is inbox-only during beta (waiting on app audit). Your clip will be saved to TikTok drafts — complete the post inside the TikTok app.

!!! tip "Scheduled publishes"
    Docker: keep the `beat` service up (`docker compose ps`). Desktop installer: scheduled posts only fire while the app is running — see [Known issues](BETA_KNOWN_ISSUES.md).

---

## Step 9 — Stop qClip when done

```bash
docker compose down
```

Your jobs, clips, and settings are saved in Docker volumes and will be there next time you start. To fully wipe and start fresh, add `-v` (this deletes everything).

---

## Frequently Asked Questions

**Do I need a GitHub account to use qClip?**
No. You only need Docker Desktop and the beta package from your invite email. On Mac you also do **not** need an Apple Developer account.

**The download link sent me to GitHub and I got a 404 — what do I do?**
Reply to your invite email and ask for the `.zip` beta package. You do not need a GitHub account to run qClip.

**My license key isn't working. What format should it be?**
The key from your beta invite starts with `SCPRO-` (four hex groups with dashes). Paste the entire string. If it still fails, open **Settings → License**, click **Show details** under **This install**, and reply to your invite email with what you see.

**What features does my beta key unlock?**
Everything — full access, no limits. Your beta key is equivalent to the highest tier.

**Does qClip send my videos to the cloud?**
No. All processing happens on your machine inside Docker containers. Your videos never leave unless you publish to YouTube/TikTok through the publish flow.

**Can I run qClip on a Mac or Linux machine?**
Yes. **Mac is a supported beta path via Docker** — follow the macOS tab in [Get qClip](BETA_DOWNLOAD.md). Linux works the same with `docker compose up -d`. NVENC hardware encoding needs NVIDIA (Windows/Linux). Mac runs CPU encode (slower, supported). The one-click `.dmg` is not ready yet; builders see [macOS installer notes](MACOS_INSTALLER.md).

**The app is running but clips are taking way too long. Help?**
On **Windows**: enable GPU in Docker Desktop → Settings → Resources → GPU, then `docker compose exec worker nvidia-smi`. On **Mac**: slow jobs are normal without NVIDIA — try a shorter source video for beta, and give Docker more CPUs/RAM under Settings → Resources.

**TikTok says "upload to inbox" instead of publishing directly. Is that a bug?**
No — this is expected during beta. TikTok restricts direct publish until an app audit is complete. Your clip will be in TikTok drafts; post it from within the TikTok app.

**How do I update qClip when a new beta version ships?**
You'll get an email. Pull the new files (or re-extract the zip), then:
```bash
docker compose pull
docker compose up -d
```

**Where do I report bugs or feedback?**
Use **Report a bug** or **Beta feedback** in the app header (top bar). Every submission is logged and read. You can also reply to your invite email.

**What information should I include in a bug report?**
- The job ID (shown on the job detail page)
- Your GPU model (or "no GPU / CPU only")
- The last 50 lines of logs: `docker compose logs api worker --tail 50`
- What you expected vs. what happened

---

## Cheat sheet

| Task | Command / Location |
|------|--------------------|
| Start qClip (Windows) | `.\scripts\start_local.ps1` |
| Start qClip (Mac manual) | `docker compose up -d` |
| Stop qClip | `docker compose down` |
| Check health (Windows, Docker) | `.\scripts\verify_stack.ps1` or **Settings → Get started** |
| Check health (Mac, Docker) | `docker compose ps` or **Settings → Get started** |
| Check health (Windows `.exe`) | **Settings → Get started** — should show **Ready** |
| View logs (Docker) | `docker compose logs api worker --tail 50` |
| Check GPU in worker (NVIDIA Docker hosts) | `docker compose exec worker nvidia-smi` |
| App URL | [http://localhost:3000](http://localhost:3000) |
| In-app Help | Header → **Help** |
| Settings → License | Activate your beta key here |
| Settings → Distribution | Connect YouTube Shorts / TikTok |

---

*Phase 0 beta · [Tutorials](tutorials/TUTORIAL_INSTALL.md) · [Known issues](BETA_KNOWN_ISSUES.md) · [Full test plan](BETA_TESTER_PLAN.md) · Questions? Reply to your invite email.*
