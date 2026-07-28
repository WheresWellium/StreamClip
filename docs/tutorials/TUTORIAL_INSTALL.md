# Tutorial — Install qClip (desktop)

**Time:** ~15 minutes · **Prerequisite:** [Beta quickstart](../BETA_TESTER_QUICKSTART.md)

This tutorial walks through the **recommended install path** for Phase 0 beta: the **Windows `.exe` or macOS `.dmg` desktop installer**. Creators do **not** need Docker.

!!! tip "Operators only"
    Prefer Docker compose? See [Optional Docker](#optional-docker-operators-only) at the bottom, or [Get qClip](../BETA_DOWNLOAD.md) Docker tabs.

---

## What you need

| Requirement | Windows | macOS |
|-------------|---------|-------|
| OS | Windows 10/11 64-bit | macOS 12+ Apple Silicon |
| Runtime | `qClip-Setup-win-x64.exe` | `qClip-mac-arm64.dmg` |
| RAM | 16 GB min / 32 GB recommended | Same |
| GPU | NVIDIA recommended | CPU / VideoToolbox (expected) |
| Accounts | **None required** to install or run | Same |

!!! tip "No GitHub account needed"
    Use the installer from your invite kit — [Get qClip](../BETA_DOWNLOAD.md). Anonymous GitHub release URLs 404 on the private repo.

---

## Step 1 — Get the installer

From your invite email / Drive / Lemon Squeezy kit:

- Windows: `installers/qClip-Setup-win-x64.exe`
- macOS: `installers/qClip-mac-arm64.dmg`

Operator rebuild (optional):

```powershell
.\scripts\fetch_desktop_artifacts.ps1 -Tag v1.0.0-beta.5
.\scripts\prepare_beta_kit.ps1 -IncludeInstaller -Tag v1.0.0-beta.5
```

---

## Step 2 — Install

=== "Windows"

    1. Run `qClip-Setup-win-x64.exe`
    2. If **SmartScreen** appears: **More info → Run anyway**
    3. Finish NSIS setup
    4. Launch **qClip** from the Start menu

=== "macOS"

    1. Open `qClip-mac-arm64.dmg`
    2. Drag **qClip** to **Applications**
    3. Unsigned beta: **right-click → Open → Open**
    4. Launch from Applications

!!! note "First run"
    First launch may download Whisper/YOLO models (multi-GB). Allow disk space and time. No Docker pull is involved.

---

## Step 3 — Verify you're ready

1. Launch the **qClip** desktop app
2. Go to **Settings → Get started**
3. **Ready** — proceed to [First job](TUTORIAL_FIRST_JOB.md). **Needs attention** — open **Help → Troubleshooting** before creating jobs.

| Check | Expected |
|-------|----------|
| **Settings → Get started** | **Ready** |
| Logs folder | Windows `%LOCALAPPDATA%\qClip\logs\` · Mac `~/Library/Application Support/qClip/logs/` |

!!! warning "Stop if not ready"
    Do **not** create jobs until **Get started** shows **Ready**. Post logs via **Report a bug** or your beta channel. See [Troubleshooting](TUTORIAL_TROUBLESHOOTING.md).

Human smoke checklist: [HUMAN_DESKTOP_SMOKE.md](../HUMAN_DESKTOP_SMOKE.md) · gate: [DESKTOP_SOLO_GATE.md](../DESKTOP_SOLO_GATE.md).

---

## Step 4 — Account and license (optional)

1. **Sign up** is optional for local beta — defaults work without API keys
2. **License key** (from invite email) is optional for Phase 0 technical testing; paste in **Settings → License** when you have one

Beta keys unlock full access. Without a key, most local pipeline features still work for T0-1 through T0-4 flows.

---

## Step 5 — Quit when done

Quit the **qClip** app. Data persists under the OS app-data directory.

---

## Next steps

| Tutorial | What you'll do |
|----------|----------------|
| [First job](TUTORIAL_FIRST_JOB.md) | Submit a URL and watch live progress |
| [GPU setup](TUTORIAL_GPU_SETUP.md) | Enable NVIDIA on Windows |
| [Troubleshooting](TUTORIAL_TROUBLESHOOTING.md) | Top failures and fixes |

---

## Optional: Docker (operators only)

Not the creator path. Use only for self-host compose:

=== "Windows"

    1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (WSL2)
    2. Extract the beta zip / clone repo
    3. `.\scripts\start_local.ps1`
    4. Open [http://localhost:3000](http://localhost:3000); re-check with `.\scripts\verify_stack.ps1`

=== "macOS"

    ```bash
    cp .env.example .env
    docker compose up -d --build
    docker compose exec -T api alembic upgrade head
    open http://localhost:3000
    ```

Stop with `docker compose down`. Details: [BETA_DOWNLOAD.md](../BETA_DOWNLOAD.md).

---

*See also: [Beta quickstart](../BETA_TESTER_QUICKSTART.md) · [Known issues](../BETA_KNOWN_ISSUES.md) · [Get qClip](../BETA_DOWNLOAD.md)*
