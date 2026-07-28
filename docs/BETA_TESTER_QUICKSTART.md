# qClip Beta — Quickstart Guide

Welcome to the qClip beta. This guide takes you from **zero to your first short clip**. Most people finish setup in about **15 minutes**.

**Creators do not need Docker.** Install the Windows `.exe` or macOS `.dmg` from your invite kit.

---

## The short version

1. Install the **desktop app** for your OS (Windows `.exe` or macOS `.dmg`) — **no Docker required**
2. Open **qClip**, sign up / log in, paste your **license key** in **Settings → License**
3. Paste a **public video link** and wait for clips to appear

**Ways to run qClip**

| Way | Best for | Notes |
|-----|----------|-------|
| **Windows installer (.exe)** | Windows creators | [Get qClip](BETA_DOWNLOAD.md) — SmartScreen → More info → Run anyway |
| **macOS installer (.dmg)** | Apple Silicon creators | `qClip-mac-arm64.dmg` — unsigned beta: **right-click → Open** |
| **Docker** (optional) | Operators / full-stack self-host | See [optional Docker appendix](#optional-docker-operators-only) |

You do **not** need a GitHub account, Python, Docker Desktop, or coding experience for the desktop path.

**Help in the app:** Open **Help** from the header for quickstart, install, GPU, and troubleshooting — without leaving qClip.

**Solo gate / smoke:** Operators validating installs use [DESKTOP_SOLO_GATE.md](DESKTOP_SOLO_GATE.md) and [HUMAN_DESKTOP_SMOKE.md](HUMAN_DESKTOP_SMOKE.md).

---

## Before you start

**You need:**

- **Windows 10/11** or **macOS 12+** (Apple Silicon for the Mac `.dmg`)
- The desktop installer from your invite (`qClip-Setup-win-x64.exe` or `qClip-mac-arm64.dmg`)
- 16 GB RAM minimum — 32 GB recommended
- On Windows: NVIDIA GPU recommended (CPU-only works but is much slower)
- On Mac: VideoToolbox / CPU (no NVIDIA) — allow longer job times
- Your license key from the invite email (looks like `SCPRO-XXXX-XXXX-XXXX-XXXX`)

**Simple words**

| Term | What it means |
|------|----------------|
| Installer | The `.exe` (Windows) or `.dmg` (Mac) that installs qClip |
| License key | Unlock code from your invite email |
| Job | One video you are processing |
| Clip | One short video cut from that job |

**You do not need:**

- Docker Desktop
- A GitHub account
- Python or Node.js installed
- An Apple Developer account (Mac)
- Any cloud subscription
- To understand programming or the command line

---

## Step 1 — Install the desktop app

=== "Windows"

    1. From your invite kit / Drive link, open `installers\qClip-Setup-win-x64.exe` (or `qClip-Setup-win-x64.exe`)
    2. If **SmartScreen** appears: **More info → Run anyway**
    3. Finish the installer, then launch **qClip** from the Start menu
    4. Wait for the splash → main UI (first run may download models — allow time and disk)

=== "macOS"

    1. Open `qClip-mac-arm64.dmg` from your invite kit
    2. Drag **qClip** to **Applications**
    3. Unsigned beta: **right-click → Open → Open** (Gatekeeper)
    4. Wait for splash → main UI

!!! tip "Step-by-step install"
    See the [Install tutorial](tutorials/TUTORIAL_INSTALL.md) for numbered steps and platform notes.

---

## Step 2 — Confirm everything is running

1. Open the **qClip** app (not a browser install step)
2. Go to **Settings → Get started** (or finish **Onboarding** on first launch)
3. You should see **Ready** — you can create a job. If you see **Needs attention**, open **Help → Troubleshooting** before submitting URLs.

Desktop logs (for bug reports):

- Windows: `%LOCALAPPDATA%\qClip\logs\`
- macOS: `~/Library/Application Support/qClip/logs/`

---

## Step 3 — Account (optional)

1. In the app, **Sign up** is optional for local Phase 0 testing — pipeline flows work without an account
2. Create an account when you want persisted settings, vault ownership, or distribution OAuth tied to a user

!!! tip "Forgot your password?"
    Use the **Forgot password?** link on the login page. A reset link will be sent to your email if SMTP is configured by the operator. For local installs, your operator can reset it manually.

---

## Step 4 — Activate your license key (optional)

1. Go to **Settings → License**
2. Paste the license key from your invite email (format: `SCPRO-…` with dashes)
3. Click **Activate** — a confirmation shows your features are unlocked

Your beta key gives you **full access to every feature** — no paywalls, no feature gates. Skip this step if your invite is for technical pipeline testing only (T0-1 … T0-4).

---

## Step 5 — Your first clip

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

## Step 6 — Approve clips and publish

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

## Step 7 — Quit when done

Quit **qClip** from the app menu / tray. Your jobs and settings stay under the app data folder for the next launch.

---

## Frequently Asked Questions

**Do I need Docker?**
No. Creators use the Windows `.exe` or macOS `.dmg`. Docker is only for operators who want the full compose stack.

**Do I need a GitHub account to use qClip?**
No. Use the installer from your invite. On Mac you do **not** need an Apple Developer account for unsigned beta (**right-click → Open**).

**The download link sent me to GitHub and I got a 404 — what do I do?**
Reply to your invite email and ask for the invite kit / Drive package. Anonymous GitHub release URLs 404 on the private repo.

**My license key isn't working. What format should it be?**
The key from your beta invite starts with `SCPRO-` (four hex groups with dashes). Paste the entire string. If it still fails, open **Settings → License**, click **Show details** under **This install**, and reply to your invite email with what you see.

**What features does my beta key unlock?**
Everything — full access, no limits. Your beta key is equivalent to the highest tier.

**Does qClip send my videos to the cloud?**
No. All processing happens on your machine. Your videos never leave unless you publish to YouTube/TikTok through the publish flow.

**Can I run qClip on a Mac?**
Yes. Use `qClip-mac-arm64.dmg` — no Docker. See [Get qClip](BETA_DOWNLOAD.md). Unsigned beta: **right-click → Open**.

**The app is running but clips are taking way too long. Help?**
On **Windows desktop**: NVIDIA + NVENC helps most. On **Mac**: slow jobs are normal without NVIDIA — try a shorter source for beta.

**TikTok says "upload to inbox" instead of publishing directly. Is that a bug?**
No — this is expected during beta. TikTok restricts direct publish until an app audit is complete. Your clip will be in TikTok drafts; post it from within the TikTok app.

**How do I update qClip when a new beta version ships?**
You'll get an email with a new installer (or kit). Install over the previous version. Auto-update is not the primary beta path yet.

**Where do I report bugs or feedback?**
Use **Report a bug** or **Beta feedback** in the app header (top bar). You can also reply to your invite email.

**What information should I include in a bug report?**
- The job ID (shown on the job detail page)
- Your GPU model (or "no GPU / CPU only")
- Zip of `%LOCALAPPDATA%\qClip\logs\` (Windows) or `~/Library/Application Support/qClip/logs/` (Mac)
- What you expected vs. what happened

---

## Cheat sheet

| Task | Command / Location |
|------|--------------------|
| Start qClip | Open the installed **qClip** app |
| Stop qClip | Quit the app |
| Check health | **Settings → Get started** — should show **Ready** |
| View logs | `%LOCALAPPDATA%\qClip\logs\` / `~/Library/Application Support/qClip/logs/` |
| In-app Help | Header → **Help** |
| Settings → License | Activate your beta key here |
| Settings → Distribution | Connect YouTube Shorts / TikTok |

---

## Optional: Docker (operators only)

Skip this entire section unless you are self-hosting the compose stack.

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. Extract the beta repo/zip, then:

=== "Windows"

    ```powershell
    .\scripts\start_local.ps1
    ```

=== "macOS"

    ```bash
    cp .env.example .env    # skip if .env exists
    docker compose up -d --build
    docker compose exec -T api alembic upgrade head
    ```

3. Open [http://localhost:3000](http://localhost:3000) · verify with `.\scripts\verify_stack.ps1` or `docker compose ps`
4. Stop with `docker compose down`

See [Get qClip](BETA_DOWNLOAD.md) Docker tabs for details.

---

*Phase 0 beta · [Install tutorial](tutorials/TUTORIAL_INSTALL.md) · [Known issues](BETA_KNOWN_ISSUES.md) · [Solo gate](DESKTOP_SOLO_GATE.md) · Questions? Reply to your invite email.*
