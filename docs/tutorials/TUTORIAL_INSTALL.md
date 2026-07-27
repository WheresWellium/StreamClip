# Tutorial — Install qClip (Docker)

**Time:** ~15 minutes · **Prerequisite:** [Beta quickstart](../BETA_TESTER_QUICKSTART.md)

This tutorial walks through the **recommended install path** for Phase 0 beta: Docker Desktop + `start_local.ps1` on Windows, with macOS equivalents where they differ.

!!! tip "Windows one-click installer"
    Using the `.exe` from [Get qClip](../BETA_DOWNLOAD.md#one-click-installers)? Skip Docker steps — open the app and use **Settings → Get started** until you see **Ready**.

---

## What you need

| Requirement | Windows | macOS |
|-------------|---------|-------|
| OS | Windows 10/11 64-bit | macOS 12+ |
| Runtime | [Docker Desktop](https://www.docker.com/products/docker-desktop/) (WSL2) | Docker Desktop for Mac (Apple Silicon or Intel) |
| RAM | 16 GB min / 32 GB recommended | Same |
| GPU | NVIDIA recommended | CPU-only (expected) |
| Accounts | **None required** to install or run | Same |

!!! tip "No GitHub account needed"
    Use the `.zip` from your invite email — [Get qClip](../BETA_DOWNLOAD.md).

## Step 1 — Install Docker Desktop

=== "Windows"

    1. Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
    2. Install and launch Docker Desktop
    3. Enable **WSL 2** if prompted (recommended)
    4. Wait until the taskbar whale shows **Docker Desktop is running**

=== "macOS"

    1. Download **Docker Desktop for Mac** — pick **Apple Silicon** or **Intel** to match your Mac
    2. Drag Docker to Applications and launch it
    3. Wait until the menu-bar whale shows **Docker Desktop is running**

---

## Step 2 — Get the qClip files

Extract the beta `.zip` from your invite email to a folder, for example:

- Windows: `C:\qClip`
- macOS: `~/qClip`

If your invite included a private repo link, clone with Git. When unsure, reply to your invite email.

---

## Step 3 — Start the stack (primary path)

=== "Windows"

    Open **PowerShell**, `cd` into your qClip folder, then run:

    ```powershell
    .\scripts\start_local.ps1
    ```

    This script:

    1. Checks Docker is running
    2. Creates `.env` from `.env.example` if missing
    3. Runs `docker compose up -d --build`
    4. Applies database migrations
    5. Runs `verify_stack.ps1` automatically

=== "macOS"

    Docker Desktop does not ship PowerShell by default. Use the manual equivalent:

    ```bash
    cd ~/qClip
    cp .env.example .env    # skip if .env already exists
    docker compose up -d --build
    docker compose exec -T api alembic upgrade head
    ```

    Optional — if [PowerShell Core](https://github.com/PowerShell/PowerShell) is installed:

    ```bash
    pwsh -File ./scripts/start_local.ps1
    ```

!!! note "First run"
    Docker downloads images (~2–5 GB). Allow 5–15 minutes on a good connection.

---

## Step 4 — Verify you're ready

**In the app (all paths):**

1. Open [http://localhost:3000](http://localhost:3000) (Docker) or launch the desktop app (`.exe`)
2. Go to **Settings → Get started**
3. **Ready** — proceed to [First job](TUTORIAL_FIRST_JOB.md). **Needs attention** — open **Help → Troubleshooting** before creating jobs.

**Docker only (optional):**

=== "Windows"

    `start_local.ps1` already runs verify. To re-check later:

    ```powershell
    .\scripts\verify_stack.ps1
    ```

=== "macOS"

    ```bash
    docker compose ps
    curl -s http://localhost:8000/api/health
    open http://localhost:3000
    ```

    Or: `pwsh -File ./scripts/verify_stack.ps1`

**Pass criteria:** **Ready** in the app, or all checks green from `verify_stack.ps1` (Windows) / healthy containers (Mac).

| Check | Expected |
|-------|----------|
| **Settings → Get started** | **Ready** |
| [http://localhost:3000](http://localhost:3000) | qClip home screen |

!!! warning "Stop if not ready"
    Do **not** create jobs until **Get started** shows **Ready** (or Docker verify passes). Post output via **Report a bug** or your beta channel. See [Troubleshooting](TUTORIAL_TROUBLESHOOTING.md).

---

## Step 5 — Account and license (optional)

1. Open [http://localhost:3000](http://localhost:3000)
2. **Sign up** is optional for local beta — defaults work without API keys
3. **License key** (from invite email) is optional for Phase 0 technical testing; paste in **Settings → License** when you have one

Beta keys unlock full access. Without a key, most local pipeline features still work for T0-1 through T0-4 flows.

---

## Step 6 — Stop when done

```bash
docker compose down
```

Data persists in Docker volumes. Add `-v` only to wipe everything.

---

## Next steps

| Tutorial | What you'll do |
|----------|----------------|
| [First job](TUTORIAL_FIRST_JOB.md) | Submit a URL and watch live progress |
| [GPU setup](TUTORIAL_GPU_SETUP.md) | Enable NVIDIA on Windows |
| [Troubleshooting](TUTORIAL_TROUBLESHOOTING.md) | Top failures and fixes |

---

*See also: [Beta quickstart](../BETA_TESTER_QUICKSTART.md) · [Known issues](../BETA_KNOWN_ISSUES.md)*
