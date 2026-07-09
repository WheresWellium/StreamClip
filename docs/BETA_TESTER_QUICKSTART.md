# StreamClip Beta — Quickstart Guide

Welcome to the StreamClip beta. This guide walks you through everything from first install to your first published clip. Most people are running in under 15 minutes.

---

## Before you start

**You need:**

- **Windows 10/11** or **macOS 12+** (Apple Silicon preferred on Mac)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running (free)
- 16 GB RAM minimum — 32 GB recommended
- On Windows: NVIDIA GPU recommended (CPU-only works but is much slower)
- On Mac: CPU-only is expected (no NVIDIA / NVENC) — allow longer job times
- The beta package (`.zip`) or private repo link from your invite email
- Your license key from the same invite email

**You do not need:**

- A GitHub account
- Python or Node.js installed
- An Apple Developer account (Mac)
- Any cloud subscription

Shorter OS-specific install: [Get StreamClip](BETA_DOWNLOAD.md).

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

## Step 2 — Get the StreamClip files

**Option A — ZIP download (easiest)**

Extract the beta `.zip` from your invite email to any folder (e.g. `C:\StreamClip` or `~/StreamClip`).

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

## Step 3 — Configure (one command)

`cd` into your StreamClip folder, then:

=== "Windows"

    ```powershell
    Copy-Item .env.example .env
    ```

=== "macOS"

    ```bash
    cp .env.example .env
    ```

The defaults work for local beta — no API keys or accounts required to start.

---

## Step 4 — Start StreamClip

```bash
docker compose up -d
```

(The same command works in PowerShell and Terminal.)

The first time you run this, Docker downloads images (~2–5 GB). Allow 5–10 minutes on a good connection (Mac may take a bit longer). After that, starts take about 30–60 seconds.

---

## Step 5 — Confirm everything is running

=== "Windows"

    ```powershell
    .\scripts\verify_stack.ps1
    ```

    All checks should be green. If any fail, **stop here** and post the output in the beta channel from your invite email before creating jobs.

=== "macOS"

    ```bash
    docker compose ps
    curl -s http://localhost:8000/api/health
    open http://localhost:3000
    ```

    Containers should be running/healthy and the health endpoint should respond. Optional: `pwsh -File ./scripts/verify_stack.ps1` if PowerShell Core is installed.

You can also open these links to confirm:

- **App:** [http://localhost:3000](http://localhost:3000) — you should see the StreamClip home screen
- **API:** [http://localhost:8000/api/health](http://localhost:8000/api/health) — should show `"status": "ok"`

---

## Step 6 — Create your account and log in

1. Open [http://localhost:3000](http://localhost:3000)
2. Click **Sign up** and create an account with your email and a password
3. Log in — check **Remember me** to stay signed in between sessions

!!! tip "Forgot your password?"
    Use the **Forgot password?** link on the login page. A reset link will be sent to your email if SMTP is configured by the operator. For local installs, your operator can reset it manually.

---

## Step 7 — Activate your license key

1. Go to **Settings → License**
2. Paste the license key from your invite email (format: `SCBETA-...`)
3. Click **Activate** — a confirmation shows your features are unlocked

Your beta key gives you **full access to every feature** — no paywalls, no feature gates.

---

## Step 8 — Your first clip

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

## Step 9 — Approve clips and publish

1. Open a finished clip → review the preview
2. Click **Approve** on clips you want to keep
3. To publish to **YouTube Shorts**:
   - Go to **Settings → Distribution → Connect YouTube Shorts**
   - Sign in with your Google account
   - Return to the clip and click **Publish**

!!! info "TikTok"
    TikTok direct publish is inbox-only during beta (waiting on app audit). Your clip will be saved to TikTok drafts — complete the post inside the TikTok app.

---

## Step 10 — Stop StreamClip when done

```bash
docker compose down
```

Your jobs, clips, and settings are saved in Docker volumes and will be there next time you start. To fully wipe and start fresh, add `-v` (this deletes everything).

---

## Frequently Asked Questions

**Do I need a GitHub account to use StreamClip?**
No. You only need Docker Desktop and the beta package from your invite email. On Mac you also do **not** need an Apple Developer account.

**The download link sent me to GitHub and I got a 404 — what do I do?**
Reply to your invite email and ask for the `.zip` beta package. You do not need a GitHub account to run StreamClip.

**My license key isn't working. What format should it be?**
The key from your beta invite starts with `SCBETA-` or similar and includes dashes. Paste the entire string. If it still fails, check that your device ID shows in Settings → License and reply to your invite email.

**What features does my beta key unlock?**
Everything — full access, no limits. Your beta key is equivalent to the highest tier.

**Does StreamClip send my videos to the cloud?**
No. All processing happens on your machine inside Docker containers. Your videos never leave unless you publish to YouTube/TikTok through the publish flow.

**Can I run StreamClip on a Mac or Linux machine?**
Yes. **Mac is a supported beta path via Docker** — follow the macOS tab in [Get StreamClip](BETA_DOWNLOAD.md). Linux works the same with `docker compose up -d`. NVENC hardware encoding needs NVIDIA (Windows/Linux). Mac runs CPU encode (slower, supported). The one-click `.dmg` is not ready yet; builders see [macOS installer notes](MACOS_INSTALLER.md).

**The app is running but clips are taking way too long. Help?**
On **Windows**: enable GPU in Docker Desktop → Settings → Resources → GPU, then `docker compose exec worker nvidia-smi`. On **Mac**: slow jobs are normal without NVIDIA — try a shorter source video for beta, and give Docker more CPUs/RAM under Settings → Resources.

**TikTok says "upload to inbox" instead of publishing directly. Is that a bug?**
No — this is expected during beta. TikTok restricts direct publish until an app audit is complete. Your clip will be in TikTok drafts; post it from within the TikTok app.

**How do I update StreamClip when a new beta version ships?**
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
| Start StreamClip | `docker compose up -d` |
| Stop StreamClip | `docker compose down` |
| Check health (Windows) | `.\scripts\verify_stack.ps1` |
| Check health (Mac) | `docker compose ps` + `curl -s http://localhost:8000/api/health` |
| View logs | `docker compose logs api worker --tail 50` |
| Check GPU in worker (NVIDIA hosts) | `docker compose exec worker nvidia-smi` |
| App URL | [http://localhost:3000](http://localhost:3000) |
| API health | [http://localhost:8000/api/health](http://localhost:8000/api/health) |
| Settings → License | Activate your beta key here |
| Settings → Distribution | Connect YouTube Shorts / TikTok |

---

*Phase 0 beta · [Known issues](BETA_KNOWN_ISSUES.md) · [Full test plan](BETA_TESTER_PLAN.md) · Questions? Reply to your invite email.*
