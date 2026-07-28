# Get started with qClip

**Install the desktop app, unlock your license, and create your first clip — on your computer, in about 15 minutes.**

qClip turns long videos into short vertical clips. You paste a link; it downloads, transcribes, finds highlights, and renders clips locally. **Nothing uploads to our cloud** unless you choose to publish.

!!! success "What you need before you begin"
    - An invite with **`qClip-Setup-win-x64.exe`** (Windows) or **`qClip-mac-arm64.dmg`** (Mac)  
    - Your license key from email — **`SCPRO-…`**  
    - **No Docker** · **No GitHub account** · **No command line**

**Pick your platform below and follow it top to bottom.** You only need one section.

---

## Before you install

### Where the installer comes from

| Source | What to open |
|--------|----------------|
| **Invite kit zip** | `installers/qClip-Setup-win-x64.exe` or `installers/qClip-mac-arm64.dmg` |
| **Drive / email link** | Direct download from your operator |
| **Lemon Squeezy** | Receipt or checkout download page |

!!! warning "Public GitHub links will not work"
    The repo is private. Anonymous release URLs return **404**.  
    If a link fails, reply to your invite email for the kit zip or Drive link.

**Current Windows build:** `1.0.0-beta.5` · `qClip-Setup-win-x64.exe` (~487 MB, unsigned — SmartScreen is normal)

**Current Mac build:** `qClip-mac-arm64.dmg` · Apple Silicon only (M1/M2/M3/…)

### System requirements

| | Windows | macOS |
|--|---------|-------|
| **OS** | Windows 10/11 (64-bit) | macOS 12+ · Apple Silicon |
| **RAM** | 16 GB min · 32 GB ideal | Same |
| **Disk** | 10 GB+ free | 15 GB+ free |
| **GPU** | NVIDIA strongly recommended | VideoToolbox / CPU — allow longer jobs |
| **First test video** | Short public URL (10–20 min) — not a long VOD |

### Words you will see

| Term | Meaning |
|------|---------|
| **Job** | One video you asked qClip to process |
| **Clip** | One short vertical cut from that job |
| **Get started** | In-app health check — **Ready** means you can create jobs |
| **License** | Your `SCPRO-…` unlock code |
| **Vault** | Saved favorite clips |

---

## Windows

### 1 · Install

1. Open **`installers\qClip-Setup-win-x64.exe`** from your kit  
2. Double-click in Explorer → follow the wizard → **Finish**

**SmartScreen (“Windows protected your PC”):** **More info** → **Run anyway**. Expected for unsigned beta — not a sign the file is malicious.

### 2 · Launch and verify

1. **Start menu → qClip**  
2. Wait for splash → main window (first launch may download AI models — allow time)  
3. **Settings → Get started** → must show **Ready**  
4. If **Needs attention**, open **Help → Troubleshooting** before creating jobs

### 3 · Activate your license

**Settings → License** → paste full key `SCPRO-XXXX-XXXX-XXXX-XXXX` → **Activate**

Beta keys unlock **all features**. An account is optional for local testing.

### 4 · Create your first clip

1. **New job**  
2. Paste a **short public** URL (YouTube, Twitch, Kick, or `.mp4`)  
3. **Submit** → watch progress: download → transcribe → highlights → render  
4. When status is **done**, open a clip and **play** it

| Setup | ~1 hour of source video |
|-------|-------------------------|
| Windows + NVIDIA GPU | ~20–25 min |
| Windows CPU only | ~60–90+ min |

### 5 · Logs (if you need support)

```
%LOCALAPPDATA%\qClip\logs\
  sidecar.log
  electron.log
```

Win+R → paste `%LOCALAPPDATA%\qClip\logs\` → Enter

```powershell
Compress-Archive -Path "$env:LOCALAPPDATA\qClip\logs" `
  -DestinationPath "$env:USERPROFILE\Desktop\qclip-logs.zip" -Force
```

**Windows checklist:** ☐ No Docker · ☐ SmartScreen passed · ☐ Ready · ☐ License on · ☐ Short job done · ☐ Clip played · ☐ Logs exist

---

## macOS (Apple Silicon)

### 1 · Install

1. Open **`installers/qClip-mac-arm64.dmg`**  
2. Drag **qClip** to **Applications**

**Gatekeeper block:** Applications → **right-click qClip → Open → Open** (first launch only).

!!! note "DMG missing from your kit?"
    Ask your invite contact, or see [macOS DMG builders](MACOS_INSTALLER.md) if you are building for others.

### 2 · Launch and verify

1. Open **qClip** from Applications  
2. **Settings → Get started** → **Ready**

### 3 · Activate your license

**Settings → License** → paste `SCPRO-…` → **Activate**

### 4 · First clip

**New job** → short public URL → **done** → play a clip. Start with a **short** source — Mac is often slower than Windows + NVIDIA.

### 5 · Logs

```
~/Library/Application Support/qClip/logs/
```

Finder → Go → Go to Folder… → paste path above

```bash
zip -r ~/Desktop/qclip-logs.zip "$HOME/Library/Application Support/qClip/logs"
```

**Mac checklist:** ☐ No Docker · ☐ Gatekeeper passed · ☐ Ready · ☐ License on · ☐ Job done · ☐ Clip played · ☐ Logs exist

---

## After your first clip

| Goal | Guide |
|------|-------|
| Understand the job screen in depth | [Your first clip](tutorials/TUTORIAL_FIRST_JOB.md) |
| Edit title, trim, approve | [Edit & approve](tutorials/TUTORIAL_EDIT_APPROVE.md) |
| Save favorites | [Clip Vault](tutorials/TUTORIAL_VAULT.md) |
| Post to YouTube Shorts | [Publish to YouTube](tutorials/TUTORIAL_PUBLISH_YOUTUBE.md) |
| Faster processing on Windows | [GPU setup](tutorials/TUTORIAL_GPU_SETUP.md) |
| Something broke | [Troubleshooting](tutorials/TUTORIAL_TROUBLESHOOTING.md) · [Known issues](BETA_KNOWN_ISSUES.md) |

**Approve before you publish:** open a clip → **Approve** → then use **Publish** on approved clips only.

!!! info "TikTok during beta"
    Posts may land in **TikTok drafts/inbox** until app audit completes — finish inside the TikTok app.

---

## Help

| Channel | Use when |
|---------|----------|
| **Help** (in app) | First stop — guides without leaving qClip |
| **Report a bug** | Include job ID + log zip |
| **Beta feedback** | Ideas and UX notes |
| **Invite email reply** | Missing installer, kit problems |

---

## Quick answers

**Do I need Docker?**  
No. Creators use the desktop `.exe` or `.dmg`. Docker is for operators only ([see below](#operators-docker-optional)).

**Do I need GitHub?**  
No.

**License key fails?**  
Paste the **entire** key with dashes. Use **Settings → License → Show details** when emailing support.

**Why is it slow?**  
Long sources and CPU-only paths take time. Use a shorter video while learning. Windows + NVIDIA is fastest.

**Where is my video stored?**  
On your machine — not in our cloud.

**How do I update?**  
Install the new `.exe` or `.dmg` from your invite when a beta wave ships.

---

## Operators: Docker (optional)

<details markdown="1">
<summary><strong>Docker self-host — not for creators</strong></summary>

Use Docker only if you need the full compose stack (API + workers + web on localhost).

=== "Windows"

    1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (WSL2)  
    2. Extract the repo/zip → `Copy-Item .env.example .env`  
    3. `docker compose up -d`  
    4. Open [http://localhost:3000](http://localhost:3000) · verify with `.\scripts\verify_stack.ps1`

=== "macOS"

    ```bash
    cp .env.example .env
    docker compose up -d
    open http://localhost:3000
    ```

**Collaborators** (GitHub auth): `gh release download v1.0.0-beta.5 -R WheresWellium/StreamClip -p qClip-Setup-win-x64.exe`

</details>

---

*Phase 0 beta · Wellium · Questions? Reply to your invite email.*
