# Get StreamClip — Beta Access

**StreamClip** turns long videos into short vertical clips — on **your computer**, not in the cloud.

**New here?** Read this page top to bottom, or jump straight to the [15-minute quickstart](BETA_TESTER_QUICKSTART.md).

---

## Where your StreamClip files come from

The StreamClip beta files are **attached to your invite email as a `.zip`** — that email is the only place to get them. There is no public download link and no GitHub account needed.

If you don't see the attachment:

1. Check spam/junk for an email from **Wellium**, subject **BETA TEST INFO**
2. Reply to that email and ask for it to be resent
3. Do **not** search GitHub for a download — the repository is private and any link you find there will 404

---

## How you run it: Docker (the only path today)

Docker is currently the **one supported way** to run the StreamClip beta, on both Windows and Mac. It's free, well-tested, and gives you the full app.

| | |
|---|---|
| **Works on** | Windows 10/11 and macOS 12+ |
| **Time** | ~15 minutes first-time setup |
| **Accounts needed** | None — no GitHub, no Docker Hub login |

!!! note "No one-click installer yet"
    A Windows `.exe` and macOS `.dmg` are in progress but not part of the beta distribution yet. Docker is the supported path for every Phase 0 tester regardless of OS.

---

## Step 1 — Install Docker Desktop

=== "Windows"

    1. Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) — it's free
    2. Run the installer, then open Docker Desktop
    3. If prompted, enable **WSL 2** (recommended — just click through the prompt)
    4. Wait until the little whale icon in your taskbar says **"Docker Desktop is running"**

=== "macOS"

    1. Download **Docker Desktop for Mac** from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) — choose **Apple Silicon** (M1/M2/M3/M4) or **Intel** to match your Mac
    2. Open the `.dmg` file, drag **Docker** into Applications, then launch it
    3. Follow the first-run setup
    4. Wait until the menu-bar whale icon says **"Docker Desktop is running"**

**Not sure which Mac chip you have?** Click the Apple menu → **About This Mac**. If it says "Apple M1/M2/M3/M4," pick Apple Silicon. If it says "Intel," pick Intel.

---

## Step 2 — Extract your StreamClip files

1. Find the `.zip` attached to your invite email (subject **BETA TEST INFO**)
2. Extract it to a folder you'll remember, for example:
      - Windows: `C:\StreamClip`
      - Mac: `~/StreamClip` (your home folder)

That's it — no `git clone`, no GitHub sign-in.

---

## Step 3 — Start StreamClip

=== "Windows"

    Open **PowerShell**, then run:

    ```powershell
    cd C:\StreamClip
    .\scripts\start_local.ps1
    ```

    This one command creates your config file, starts Docker, sets up the database, and checks that everything is healthy — automatically.

=== "macOS"

    Open **Terminal**, then run:

    ```bash
    cd ~/StreamClip
    cp .env.example .env
    docker compose up -d --build
    docker compose exec -T api alembic upgrade head
    ```

**First run takes longer** — Docker downloads about 2–5 GB of images. Give it 5–15 minutes on a normal connection. Every time after that, starting up takes under a minute.

---

## Step 4 — Confirm it's running

=== "Windows"

    `start_local.ps1` already checked this for you. To check again anytime:

    ```powershell
    .\scripts\verify_stack.ps1
    ```

    You want to see **all checks green**. If something's red, don't create a job yet — use **Report a bug** in the app (Step 5) and paste the output.

=== "macOS"

    ```bash
    docker compose ps
    curl -s http://localhost:8000/api/health
    ```

    You want every service listed as **running**/**healthy**, and the health check to return something with `"status": "ok"`.

Either way, open your browser to confirm:

| Check | URL | You should see |
|-------|-----|-----------------|
| App | [http://localhost:3000](http://localhost:3000) | The StreamClip home screen |
| API health | [http://localhost:8000/api/health](http://localhost:8000/api/health) | `{"status": "ok", ...}` |

---

## Step 5 — Activate your license key

1. On [http://localhost:3000](http://localhost:3000), sign up or log in
2. Go to **Settings → License**
3. Paste the license key from your invite email (looks like `SCPRO-XXXX-XXXX-XXXX-XXXX`)
4. Click **Activate**

Your beta key unlocks **every feature** — there's no paywall or limited tier during the beta.

---

## Make your first clip

1. Click **New job** on the home screen
2. Paste any **public** video link — Twitch VOD, YouTube video, Kick stream, or a direct `.mp4` URL
3. Click **Submit** and watch the progress bar
4. When it says **done**, review the clip previews and click **Approve** on the ones you like

**How long does it take?**

| Your setup | ~1-hour source video |
|------------|-----------------------|
| Windows with NVIDIA GPU | ~20–25 minutes |
| Windows or Mac, CPU only | ~60–90+ minutes |

Want the full walkthrough? See the [15-minute quickstart](BETA_TESTER_QUICKSTART.md).

---

## Publish to YouTube Shorts (optional)

1. Open an approved clip
2. Go to **Settings → Distribution → Connect YouTube Shorts** and sign in with Google
3. Return to the clip and click **Publish**

!!! note "TikTok"
    During beta, TikTok publishing saves your clip to **TikTok drafts** instead of posting directly (Google/TikTok app-review limitation, not a bug). Finish posting from inside the TikTok app.

---

## Stop StreamClip when you're done

```bash
docker compose down
```

Your jobs, clips, and settings stay saved. Only add `-v` to the end of that command if you want to **permanently delete everything** and start fresh.

---

## System requirements

| | Windows | macOS |
|-|---------|-------|
| OS version | Windows 10 or 11 (64-bit) | macOS 12 or newer |
| Runtime | Docker Desktop (with WSL 2) | Docker Desktop for Mac |
| RAM | 16 GB minimum, 32 GB recommended | Same |
| Free disk space | 10 GB+ (SSD preferred) | 20 GB+ recommended |
| Graphics card | NVIDIA GPU recommended for speed — CPU-only works, just slower | No NVIDIA on Mac — CPU-only is expected and fully supported |
| Accounts | None | None |

---

## Troubleshooting

| Problem | What to do |
|---------|------------|
| The app won't load at localhost:3000 | Wait 60 seconds after starting, then run `docker compose ps` — every service should say "running" |
| `docker compose` says "command not found" | Docker Desktop isn't installed or isn't running — open it and wait for "Docker Desktop is running" |
| Clips are taking forever | On Windows: turn on GPU in Docker Desktop → Settings → Resources → GPU. On Mac: this is expected without NVIDIA — try a shorter video for testing |
| License key won't activate | Make sure you copied the whole key including every dash |
| Can't find the `.zip` attachment | Check spam for the "BETA TEST INFO" email; reply to it and ask for a resend |

More detail: [Known issues](BETA_KNOWN_ISSUES.md) · [Troubleshooting tutorial](tutorials/TUTORIAL_TROUBLESHOOTING.md)

---

## Get help

Use **Report a bug** or **Beta feedback** in the app header (top of the screen) — every submission is read, even before auto-replies are set up. You can also just reply to your invite email.

---

*Jet Stream / StreamClip · Phase 0 creator beta · [Known issues](BETA_KNOWN_ISSUES.md) · [Full quickstart](BETA_TESTER_QUICKSTART.md)*
