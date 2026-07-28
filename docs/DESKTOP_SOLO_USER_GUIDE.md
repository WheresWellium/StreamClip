# Desktop install guide

**The complete path from download to your first clip — no Docker, no terminal, no GitHub account.**

qClip is a desktop app. You install it like any other program, paste a video link, and get short clips back. Everything runs on **your** computer. Your footage never uploads to our servers unless you choose to publish.

!!! success "You are in the right place if…"
    - You received a beta invite with an installer or kit zip  
    - You want **qClip-Setup-win-x64.exe** (Windows) or **qClip-mac-arm64.dmg** (Mac)  
    - You do **not** want to install Docker  

**Time:** ~15 minutes to install and run your first short test job (plus render time).

---

## How to use this guide

| Section | What it does |
|---------|----------------|
| **[Before you begin](#before-you-begin)** | Check you have the right file and hardware |
| **[Part 1 — Windows](#part-1-windows)** | Install, unlock, first clip, logs |
| **[Part 2 — macOS](#part-2-macos-apple-silicon)** | Same flow for Apple Silicon Macs |
| **[After your first clip](#after-your-first-clip)** | Approve, publish, get help |
| **[Quick answers](#quick-answers)** | SmartScreen, Gatekeeper, speed, keys |

Pick **one** platform section and follow it top to bottom. You do not need both.

---

## Before you begin

### Get the installer (everyone)

Your invite should include one of:

| Source | What to look for |
|--------|------------------|
| **Invite kit zip** | Folder `installers/` with the `.exe` or `.dmg` inside |
| **Drive / email link** | Direct download from your operator |
| **Lemon Squeezy** | Receipt or download page from checkout |

!!! warning "Do not use public GitHub download links"
    The repo is private. Anonymous `github.com/.../releases/download/...` URLs return **404**.  
    If a link fails, reply to your invite email and ask for the **kit zip** or Drive link.

=== "Windows"

    **File:** `qClip-Setup-win-x64.exe` (~487 MB)  
    **Version:** `1.0.0-beta.5` (unsigned beta — SmartScreen warning is normal)

=== "macOS"

    **File:** `qClip-mac-arm64.dmg` (Apple Silicon only)  
    **If missing from your kit:** ask your invite contact — a Mac builder can produce it ([builder notes](MACOS_INSTALLER.md))

### What each file does

| File | Plain English |
|------|----------------|
| **`.exe` (Windows)** | The installer — double-click, qClip appears in your Start menu |
| **`.dmg` (Mac)** | A disk image — open it, drag qClip to Applications |
| **License key (`SCPRO-…`)** | Unlocks all beta features — paste once in **Settings → License** |
| **Invite kit zip** | Installer + short docs — everything a tester needs without GitHub |

### Hardware (recommended)

| | Windows | macOS |
|--|---------|-------|
| **OS** | Windows 10 or 11 (64-bit) | macOS 12+ on **Apple Silicon** (M1/M2/M3/…) |
| **RAM** | 16 GB minimum · 32 GB ideal | Same |
| **Disk** | 10 GB+ free (models download on first run) | 15 GB+ free |
| **GPU** | NVIDIA strongly recommended | Built-in VideoToolbox / CPU — allow longer jobs |
| **Accounts** | None required to install | None required; unsigned beta uses **right-click → Open** |

---

## Part 1 — Windows

### Step 1 — Run the installer

1. Open your invite kit → **`installers\qClip-Setup-win-x64.exe`**
2. Double-click in File Explorer
3. Follow the setup wizard (defaults are fine) → **Finish**

### Step 2 — Pass SmartScreen (unsigned beta)

If you see **“Windows protected your PC”**:

1. Click **More info**
2. Click **Run anyway**

This is expected until we add code signing. It does **not** mean the file is malware — it means Windows has not seen this publisher before.

### Step 3 — Open qClip

1. **Start menu** → **qClip**
2. Wait for the splash screen, then the main window  
3. **First launch** may download AI models (Whisper, etc.) — allow several minutes and free disk space

### Step 4 — Confirm you are ready

1. Go to **Settings → Get started**
2. You want **Ready**  
3. If you see **Needs attention**, open **Help → Troubleshooting** before creating jobs

### Step 5 — Activate your license

1. **Settings → License**
2. Paste the full key from your invite email (`SCPRO-XXXX-XXXX-XXXX-XXXX`)
3. Click **Activate**

Beta keys unlock **everything** — no feature tiers during Phase 0.

!!! tip "Optional account"
    Sign up if you want saved settings and distribution OAuth tied to a user.  
    Local pipeline testing works without an account.

### Step 6 — Create your first clip (smoke test)

Use a **short** public video for the first run (10–20 minutes ideal).

1. Click **New job**
2. Paste a public link — for example:
   - YouTube: `https://www.youtube.com/watch?v=...`
   - Twitch VOD: `https://www.twitch.tv/videos/...`
3. Click **Submit**
4. Watch the progress bar: **download → transcribe → highlights → render**
5. When status is **done**, click a clip and **play** it in the app

| Setup | Rough time for ~1 hour of source video |
|-------|----------------------------------------|
| Windows + NVIDIA GPU | ~20–25 minutes |
| Windows CPU only | ~60–90+ minutes |

### Step 7 — Know where your logs live

If something breaks, support will ask for logs:

```
%LOCALAPPDATA%\qClip\logs\
  sidecar.log    ← processing engine
  electron.log   ← desktop shell
```

**Quick open:** Win+R → paste `%LOCALAPPDATA%\qClip\logs\` → Enter

**Zip for email:**

```powershell
Compress-Archive -Path "$env:LOCALAPPDATA\qClip\logs" `
  -DestinationPath "$env:USERPROFILE\Desktop\qclip-logs.zip" -Force
```

### Windows checklist

- [ ] Installed from `.exe` — **no Docker**
- [ ] SmartScreen cleared (More info → Run anyway)
- [ ] **Settings → Get started** shows **Ready**
- [ ] License activated
- [ ] One short job reached **done**
- [ ] Played a clip in-app
- [ ] Logs folder exists

---

## Part 2 — macOS (Apple Silicon)

### Step 1 — Open the disk image

1. From your kit: **`installers/qClip-mac-arm64.dmg`**
2. Double-click in Finder

### Step 2 — Install the app

1. Drag **qClip** into **Applications**
2. Eject the disk image (optional)

### Step 3 — Pass Gatekeeper (unsigned beta)

If macOS says the app “can’t be opened”:

1. **Finder → Applications**
2. **Control-click** (or right-click) **qClip**
3. Choose **Open** → confirm **Open** again

You only need this trick the **first** time. Notarization comes later for wider release.

### Step 4 — Launch and confirm ready

1. Open **qClip** from Applications  
2. Wait for splash → main UI (first run may download models)  
3. **Settings → Get started** → **Ready**

### Step 5 — Activate your license

**Settings → License** → paste `SCPRO-…` → **Activate**

### Step 6 — First clip

Same as Windows: **New job** → short public URL → **done** → play a clip.

Mac jobs are often slower than Windows + NVIDIA — start with a **short** source.

### Step 7 — Logs

```
~/Library/Application Support/qClip/logs/
  sidecar.log
  electron.log
```

**Finder:** Go → Go to Folder… → paste the path above

**Zip for email:**

```bash
zip -r ~/Desktop/qclip-logs.zip "$HOME/Library/Application Support/qClip/logs"
```

### macOS checklist

- [ ] Installed from `.dmg` — **no Docker**
- [ ] Gatekeeper cleared (right-click → Open)
- [ ] **Ready** in Get started
- [ ] License activated
- [ ] Short job **done** + clip played
- [ ] Logs folder exists

!!! note "DMG not in your kit yet?"
    Ask your invite contact. Builders on Apple Silicon can run `./scripts/build_macos_solo.sh` — see [macOS installer (builders)](MACOS_INSTALLER.md).

---

## After your first clip

### Approve and keep the good ones

1. Open a finished clip → watch the preview  
2. Click **Approve** on clips you want to keep  
3. Rejected clips stay in the job but won’t publish

### Publish to YouTube Shorts (optional)

1. **Settings → Distribution → Connect YouTube Shorts** → sign in with Google  
2. Open an **approved** clip → **Publish**

!!! info "TikTok during beta"
    Direct publish may route to **TikTok drafts/inbox** until app audit completes. Finish the post inside the TikTok app — [known issues](BETA_KNOWN_ISSUES.md).

### Quit the app

Use **File → Quit** or close from the tray. Your jobs and database stay on disk for next launch.

### Get help

| Channel | When to use it |
|---------|----------------|
| **Help → Troubleshooting** (in app) | First stop — same topics as this site |
| **Report a bug** (header) | Something broke — include job ID + log zip |
| **Beta feedback** (header) | Ideas and UX notes |
| **Reply to invite email** | Download problems, missing kit, human escalation |

**Next reads:** [Your first clip (detailed)](tutorials/TUTORIAL_FIRST_JOB.md) · [Troubleshooting](tutorials/TUTORIAL_TROUBLESHOOTING.md) · [Known issues](BETA_KNOWN_ISSUES.md)

---

## Quick answers

**Do I need Docker?**  
No. Docker is for operators who self-host the full server stack. Creators use the `.exe` or `.dmg`.

**Do I need a GitHub account?**  
No.

**My license key fails**  
Paste the **entire** key including dashes. In **Settings → License → Show details**, copy what you see and email support.

**Why is processing slow?**  
Long sources + CPU-only paths take time. Use a shorter video for beta testing. Windows + NVIDIA is fastest.

**Where is my video stored?**  
On your machine under qClip’s app data folder — not in our cloud.

**How do I update later?**  
Your invite email will include a new installer. Install over the previous version.

---

## Words you will see in the app

| Term | Meaning |
|------|---------|
| **Job** | One video you asked qClip to process |
| **Clip** | One short vertical cut from that job |
| **Vault** | Saved favorite clips |
| **Get started** | Health check — **Ready** means you can create jobs |
| **License** | Your `SCPRO-…` unlock code |

---

*Phase 0 beta · [Get installer details](BETA_DOWNLOAD.md) · [15-minute quickstart](BETA_TESTER_QUICKSTART.md)*
