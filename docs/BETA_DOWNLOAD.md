# Get qClip — Beta Access


> **Current Windows installer:** `1.0.0-beta.5` (2026-07-27) — `qClip-Setup-win-x64.exe` (~487 MB).  
> **macOS product path:** `qClip-mac-arm64.dmg` (Apple Silicon) — desktop app, **no Docker**.  
> **Testers:** get installers from your **invite kit zip** (`installers/`), **Lemon Squeezy** receipt, or **operator Drive** link — not from GitHub.  
> GitHub release URLs are **collaborator-only**; anonymous browser hits return **404**.


**qClip** turns long videos into short vertical clips — on **your computer**, not in the cloud.

**New here?** Read this page top to bottom, or jump to the [15-minute quickstart](BETA_TESTER_QUICKSTART.md).

---

## Choose how you want to run it

| Option | Who it's for | Difficulty |
|--------|--------------|------------|
| **Windows installer (.exe)** | Creators who want a normal desktop app | Easy — download and install |
| **macOS installer (.dmg)** | Apple Silicon Mac creators (desktop product path) | Easy — drag to Applications; unsigned beta may need **right-click → Open** |
| **Docker (Windows or Mac)** | Operators / full-stack self-host | Medium — install Docker once, then one command |

Desktop installers are free for invited beta testers. The **Windows `.exe`** and **macOS `.dmg`**
ship in the invite kit zip under `installers/` (when available), via Lemon Squeezy, or an
operator Drive link — **not** via public GitHub. The repo is private; anonymous
`/releases/.../download/...` URLs **404**.

---

## What's available right now

| Path | Status | Who it's for |
|------|--------|--------------|
| **Windows one-click installer (.exe)** | ✅ Ready (unsigned beta) | Creators who want no Docker — SmartScreen may warn |
| **macOS one-click installer (.dmg)** | ✅ Product path (Apple Silicon) | Creators — use the DMG; unsigned beta → **right-click → Open** |
| **Docker self-host (Windows)** | ✅ Ready | Operators / testers who prefer compose |
| **Docker self-host (macOS)** | ✅ Optional | Operators only — **not** required for the desktop app |

**Phase 0 testers:** prefer the **desktop installer** for your OS. Docker remains available for
full-stack verify and operators.

---

## Windows installer (no Docker)

1. Get **`qClip-Setup-win-x64.exe`** (~487 MB) from one of:
   - Your **invite kit zip** → `installers/qClip-Setup-win-x64.exe`
   - **Lemon Squeezy** receipt / download page (if your invite used LS)
   - An **operator Drive** (or similar) link from your invite email
2. Run the installer

Do **not** rely on the GitHub Releases “latest download” URL — the repo is private and anonymous downloads return **404**.

**If Windows shows "Windows protected your PC"**

This is normal for an unsigned beta build. It does **not** mean the file is a virus.

1. Click **More info**
2. Click **Run anyway**
3. Finish install and open qClip from the Start menu
4. Sign up or log in, then paste your license key in **Settings → License**

The desktop app runs everything locally. You still need your **license key** from your invite email.

### For collaborators

Repo collaborators (authenticated GitHub access) can pull the Windows installer with:

```powershell
gh release download v1.0.0-beta.5 -R WheresWellium/StreamClip -p qClip-Setup-win-x64.exe
```

Or open the [v1.0.0-beta.5](https://github.com/WheresWellium/StreamClip/releases/tag/v1.0.0-beta.5) release page while signed in.

---

## macOS installer (no Docker)

**Product path for Mac creators:** the Apple Silicon **`.dmg`**. You do **not** need Docker,
Xcode, Node, or Python.

1. Get **`qClip-mac-arm64.dmg`** from your invite kit (`installers/`), Lemon Squeezy, or operator link
2. Open the DMG and drag **qClip** to **Applications**
3. First launch (unsigned beta): Finder → **Applications** → **right-click qClip → Open** → **Open**
   - Gatekeeper may warn until the build is Developer ID–signed and notarized — that is expected for unsigned beta
4. Sign up or log in, then paste your license key in **Settings → License**

**Requirements:** macOS 12+, Apple Silicon (M1/M2/M3/M4). Intel Mac `.dmg` is not shipped yet.

**If the DMG is not in your kit yet:** ask your invite contact for the latest `qClip-mac-arm64.dmg`,
or use Docker below as a temporary operator fallback — not the preferred creator path.

### For collaborators / builders

Builders produce the DMG on a Mac with:

```bash
./scripts/build_desktop_installer_macos.sh
```

Details: [macOS installer guide](MACOS_INSTALLER.md) (builder notes live in-repo at `packaging/installer/MACOS.md`).

---

## Docker install (optional — operators)

Docker is **optional**. Prefer the Windows `.exe` or macOS `.dmg` for day-to-day beta use.
Use Docker when you want the full compose stack (API + workers + web) for operator verify.

=== "Windows"

    ### Requirements

    - **Windows 10 or 11** (64-bit)
    - **Docker Desktop** — [download](https://www.docker.com/products/docker-desktop/) (WSL2 backend)
    - **16 GB RAM** minimum (32 GB recommended)
    - **NVIDIA GPU** strongly recommended — CPU-only works but is much slower

    ### Step 1 — Get the beta package

    You should have received a `.zip` or a private repo link in your invite email.

    ### Step 2 — Extract and set up

    ```powershell
    cd streamclip
    Copy-Item .env.example .env
    ```

    ### Step 3 — Start qClip

    ```powershell
    docker compose up -d
    ```

    First run downloads Docker images — allow 5–10 minutes on a fast connection.

    ### Step 4 — Verify it's running

    ```powershell
    .\scripts\verify_stack.ps1
    ```

    Or open:

    - **App:** [http://localhost:3000](http://localhost:3000)
    - **API health:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

=== "macOS"

    ### Requirements

    - **macOS 12+** (Apple Silicon preferred)
    - **Docker Desktop for Mac** — only if you choose this operator path
    - **16 GB RAM** minimum (32 GB recommended)

    Prefer the **`.dmg`** above unless you specifically need compose.

    ```bash
    cp .env.example .env
    docker compose up -d
    docker compose ps
    curl -s http://localhost:8000/api/health
    open http://localhost:3000
    ```

---

## After install

### Desktop installer (Windows `.exe` or macOS `.dmg`)

1. Open **qClip** (Start menu / Applications)
2. Complete first-run onboarding if prompted
3. Go to **Settings → License** and paste your invite key
4. Confirm activation before starting a job

Engine + UI listen on `http://127.0.0.1:8765` (desktop sidecar).

### Docker path

1. Open the UI at [http://localhost:3000](http://localhost:3000)
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
| Windows / Mac CPU-only (desktop or Docker) | ~60–90+ minutes |
| Mac desktop (Apple Silicon / VideoToolbox) | Faster than pure CPU when VT is available |

### Publish to YouTube Shorts (optional)

1. Open a finished, approved clip
2. **Settings → Distribution → Connect YouTube Shorts** → sign in with Google
3. Click **Publish** on any approved clip

!!! note "TikTok"
    TikTok direct publish is inbox-upload only during beta (awaiting app audit). Your clip will be saved to TikTok drafts — finish posting inside the TikTok app.

### Stop qClip

- **Desktop:** quit the app (sidecar stops with the window/tray).
- **Docker:** `docker compose down` (add `-v` only to wipe volumes).

---

## System requirements

| | Windows desktop | macOS desktop | Docker (optional) |
|-|-----------------|---------------|-------------------|
| OS | Windows 10/11 64-bit | macOS 12+ Apple Silicon | Same OS + Docker Desktop |
| Artifact | `qClip-Setup-win-x64.exe` | `qClip-mac-arm64.dmg` | compose stack |
| RAM | 16 GB min / 32 GB recommended | Same | Same |
| Disk | 10 GB+ free | 15 GB+ free | 20 GB+ free |
| GPU | NVIDIA + NVENC recommended | VideoToolbox / CPU | NVIDIA on Windows; CPU on Mac |
| Accounts | License key | License key; right-click Open if unsigned | License key |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Mac: “app can’t be opened” / Gatekeeper | **Right-click → Open** (unsigned beta). Notarized builds won’t need this |
| Windows: “Windows protected your PC” | **More info → Run anyway** |
| App won’t load (Docker) | Wait 60 s after `docker compose up -d`; run `docker compose ps` |
| License key not accepted | Paste the full key including dashes; **Settings → License → Show details** if support asks |
| Very slow clips on Mac | Expected without NVIDIA; prefer shorter sources for beta; desktop VT helps when available |
| Missing `qClip-mac-arm64.dmg` in kit | Ask invite contact; builders see [MACOS_INSTALLER.md](MACOS_INSTALLER.md) |

---

## Get help

Use **Report a bug** or **Beta feedback** in the app header — every submission is read even if auto-reply isn't set up yet. Or reply directly to your invite email.

---

## One-click installers

| Platform | Artifact | Status |
|----------|----------|--------|
| Windows | `qClip-Setup-win-x64.exe` | ✅ **v1.0.0-beta.5** — invite kit / Lemon Squeezy / Drive; unsigned; SmartScreen → More info → Run anyway |
| macOS | `qClip-mac-arm64.dmg` | ✅ **Product path** — Apple Silicon DMG; unsigned beta → right-click → Open; builders: [MACOS_INSTALLER.md](MACOS_INSTALLER.md) |

**Collaborator release page:** [v1.0.0-beta.5](https://github.com/WheresWellium/StreamClip/releases/tag/v1.0.0-beta.5) (GitHub auth required)

Desktop installers are the creator path. Docker remains available for operator / full-stack verify.

---

*qClip · Phase 0 creator beta · [Known issues](BETA_KNOWN_ISSUES.md) · [Full quickstart](BETA_TESTER_QUICKSTART.md)*
