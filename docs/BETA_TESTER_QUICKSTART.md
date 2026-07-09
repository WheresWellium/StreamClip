# StreamClip Beta — Quickstart Guide

Welcome to the StreamClip beta. This guide takes you from **zero to your first short clip**. Most people finish setup in about **15 minutes**.

---

## The short version

1. Install **Docker Desktop** (free) and make sure it's running
2. Extract the `.zip` attached to your invite email and run **one start command**
3. Open **http://localhost:3000** in your browser
4. Paste a **public video link** and wait for clips to appear
5. Paste your **license key** in **Settings → License** (from the same invite email)

You do **not** need a GitHub account, Python, Node.js, or any coding experience. Everything you need is attached to your invite email.

---

## Before you start

**You need:**

- **Windows 10/11** or **macOS 12+** (Apple Silicon preferred on Mac, Intel works too)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running (free)
- 16 GB RAM minimum — 32 GB recommended
- The `.zip` attached to your invite email (subject: **BETA TEST INFO**)
- Your license key from that same email (looks like `SCPRO-XXXX-XXXX-XXXX-XXXX`)
- On Windows: an NVIDIA GPU speeds things up a lot, but CPU-only works too
- On Mac: CPU-only is expected — there's no NVIDIA GPU support on Mac, and that's fine for beta testing

**Simple words**

| Term | What it means |
|------|----------------|
| Docker | Free app that runs StreamClip locally on your machine |
| License key | The unlock code from your invite email |
| Job | One video you've asked StreamClip to process |
| Clip | One short video cut from that job |

**You do not need:**

- A GitHub account
- Python or Node.js installed
- An Apple Developer account (Mac)
- Any cloud subscription
- To understand programming or the command line — just copy and paste the commands below

---

## Step 1 — Install Docker Desktop

If Docker Desktop isn't already installed:

=== "Windows"

    1. Download it free at [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
    2. Install and open Docker Desktop
    3. Enable **WSL 2** if prompted (recommended — just click through)
    4. Wait until the Docker whale icon in your taskbar shows **"Docker Desktop is running"**

=== "macOS"

    1. Download **Docker Desktop for Mac** — choose **Apple Silicon** or **Intel** to match your machine
    2. Open the `.dmg`, drag Docker to Applications, and launch it
    3. Complete the first-run setup
    4. Wait until the menu-bar whale icon shows **"Docker Desktop is running"**

---

## Step 2 — Extract your StreamClip files

Find the `.zip` attached to your invite email (subject **BETA TEST INFO**) and extract it to a folder you'll remember:

- Windows: something like `C:\StreamClip`
- Mac: something like `~/StreamClip`

That's the whole step — no `git clone`, no downloads page, no account sign-in.

---

## Step 3 — Start StreamClip (one command)

Open a terminal in the folder you just extracted, then run:

=== "Windows"

    ```powershell
    .\scripts\start_local.ps1
    ```

    This one command creates your config file, starts Docker, sets up the database, and checks that everything's healthy — all automatically.

=== "macOS"

    ```bash
    cp .env.example .env    # skip if .env already exists
    docker compose up -d --build
    docker compose exec -T api alembic upgrade head
    ```

    If you happen to have [PowerShell Core](https://github.com/PowerShell/PowerShell) installed, you can instead run:

    ```bash
    pwsh -File ./scripts/start_local.ps1
    ```

The defaults work for local beta testing — **no API keys or extra setup required** to start.

**First run takes a bit longer** — Docker downloads about 2–5 GB of images. Give it 5–15 minutes on a decent connection. After that, starting up takes 30–60 seconds.

!!! tip "Want more detail?"
    See the [Install tutorial](tutorials/TUTORIAL_INSTALL.md) for numbered steps and platform notes.

---

## Step 4 — Confirm everything is running

=== "Windows"

    `start_local.ps1` already checked this for you. To re-check anytime:

    ```powershell
    .\scripts\verify_stack.ps1
    ```

    You want to see **all checks green**. If anything fails, stop here and use **Report a bug** in the app header with the script's output before creating jobs.

=== "macOS"

    ```bash
    docker compose ps
    curl -s http://localhost:8000/api/health
    open http://localhost:3000
    ```

    You want every container to show **running**/**healthy**, and the health check to respond with something like `"status": "ok"`.

You can also just open these in your browser:

- **App:** [http://localhost:3000](http://localhost:3000) — you should see the StreamClip home screen
- **API:** [http://localhost:8000/api/health](http://localhost:8000/api/health) — should show `"status": "ok"`

---

## Step 5 — Account (optional)

1. Open [http://localhost:3000](http://localhost:3000)
2. **Signing up is optional** for local Phase 0 testing — the pipeline works without an account
3. Create an account when you want your settings saved, a clip vault, or to connect YouTube/TikTok

!!! tip "Forgot your password?"
    Use the **Forgot password?** link on the login page. For local installs without email configured, ask whoever set up your beta cohort to reset it manually.

---

## Step 6 — Activate your license key (optional)

1. Go to **Settings → License**
2. Paste the license key from your invite email (format: `SCPRO-…` with dashes)
3. Click **Activate** — you'll see a confirmation that your features are unlocked

Your beta key gives you **full access to every feature** — no paywalls, no limits. Feel free to skip this step if you're only testing the core pipeline.

---

## Step 7 — Your first clip

1. Click **New job** on the home screen
2. Paste any **public** video URL:
      - Twitch VOD: `https://www.twitch.tv/videos/...`
      - YouTube video: `https://www.youtube.com/watch?v=...`
      - Kick stream: `https://kick.com/...`
      - Or a direct `.mp4` URL
3. Optionally give it a title, then click **Submit**
4. Watch the progress bar — it moves through stages (download → transcribe → detect highlights → render)
5. When it says **done**, clip previews appear

**How long does it take?**

| Your setup | ~1-hour source video |
|------------|-----------------------|
| Windows with NVIDIA GPU | ~20–25 minutes |
| Windows or Mac, CPU only | ~60–90+ minutes |

---

## Step 8 — Approve clips and publish

1. Open a finished clip and review the preview
2. Click **Approve** on the ones you want to keep
3. To publish to **YouTube Shorts**:
      - Go to **Settings → Distribution → Connect YouTube Shorts**
      - Sign in with your Google account
      - Return to the clip and click **Publish**

!!! info "TikTok"
    TikTok direct publish is inbox-only during beta (waiting on app review). Your clip lands in TikTok drafts — finish the post from inside the TikTok app.

!!! tip "Scheduled publishes"
    Keep the `beat` service running (`docker compose ps`) so scheduled posts fire on time.

---

## Step 9 — Stop StreamClip when done

```bash
docker compose down
```

Your jobs, clips, and settings stay saved in Docker volumes for next time. Only add `-v` to that command if you want to wipe everything and start completely fresh.

---

## Frequently Asked Questions

**Do I need a GitHub account to use StreamClip?**
No. Everything you need — the app files and your license key — is attached to your invite email.

**I don't see a `.zip` attached to my invite email. What do I do?**
Check spam/junk for an email from Wellium with the subject "BETA TEST INFO." If it's not there, reply to your invite email and ask for it to be resent. You never need a GitHub account for any part of this.

**My license key isn't working. What format should it be?**
The key starts with `SCPRO-` followed by four groups of characters separated by dashes. Paste the entire string, dashes included. If it still fails, check that a device ID shows in Settings → License and reply to your invite email.

**What features does my beta key unlock?**
Everything — full access, no limits. Your beta key is equivalent to the highest tier.

**Does StreamClip send my videos to the cloud?**
No. All processing happens on your machine inside Docker containers. Your videos never leave your computer unless you choose to publish to YouTube or TikTok.

**Can I run StreamClip on a Mac or Linux machine?**
Yes. Mac is fully supported via Docker — follow the macOS tab above. Linux works the same way with `docker compose up -d`. Hardware video encoding (NVENC) needs an NVIDIA GPU (Windows/Linux); Mac runs on CPU, which is slower but fully supported for beta testing.

**The app is running but clips are taking way too long. Help?**
On **Windows**: enable GPU in Docker Desktop → Settings → Resources → GPU, then check it's working with `docker compose exec worker nvidia-smi`. On **Mac**: slower processing is expected without an NVIDIA GPU — try a shorter source video for testing, and give Docker more CPU/RAM under Settings → Resources.

**TikTok says "upload to inbox" instead of publishing directly. Is that a bug?**
No — this is expected during beta. TikTok restricts direct publishing until an app review completes. Your clip lands in TikTok drafts; post it from inside the TikTok app.

**How do I update StreamClip when a new beta version ships?**
You'll get a new invite email with an updated `.zip`. Extract it over your existing folder (or into a fresh one), then run:
```bash
docker compose pull
docker compose up -d
```

**Where do I report bugs or feedback?**
Use **Report a bug** or **Beta feedback** in the app header (top of the screen). Every submission is logged and read. You can also just reply to your invite email.

**What information should I include in a bug report?**
- The job ID (shown on the job detail page)
- Your GPU model (or "no GPU / CPU only")
- The last 50 lines of logs: `docker compose logs api worker --tail 50`
- What you expected vs. what actually happened

---

## Cheat sheet

| Task | Command / Location |
|------|--------------------|
| Start StreamClip (Windows) | `.\scripts\start_local.ps1` |
| Start StreamClip (Mac manual) | `docker compose up -d --build` |
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

*Phase 0 beta · [Tutorials](tutorials/TUTORIAL_INSTALL.md) · [Known issues](BETA_KNOWN_ISSUES.md) · [Full test plan](BETA_TESTER_PLAN.md) · Questions? Reply to your invite email.*
