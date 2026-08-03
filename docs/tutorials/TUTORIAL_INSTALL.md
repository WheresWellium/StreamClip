# Tutorial — Install qClip (Docker self-host)

!!! warning "Not on the public docs site"
    Creators: use **[Install qClip](../BETA_DOWNLOAD.md)** (Windows `.exe` or Mac Docker). This page is an operator deep-dive kept in the repo only.

**Time:** ~15–30 minutes · **Audience:** operators and advanced Docker self-host

**Windows creators:** prefer the one-click installer — [Install → Windows](../BETA_DOWNLOAD.md#one-click-installers).

!!! tip "Windows one-click installer"
    Download [qClip-Setup-win-x64.exe](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe) (v1.0.0-beta.24), run it, open from Start menu, paste your key in **Settings → License**. No Docker.

---

## What you need

| Requirement | Windows (Docker) | macOS |
|-------------|------------------|-------|
| OS | Windows 10/11 64-bit | macOS 12+ |
| Runtime | [Docker Desktop](https://www.docker.com/products/docker-desktop/) (WSL2) | Docker Desktop for Mac |
| RAM | 16 GB min / 32 GB recommended | Same |
| GPU | NVIDIA recommended | CPU-only (expected) |
| Project files | Repo clone or kit from operator | Same |
| Accounts | None to install or run | Same |

---

## Step 1 — Install Docker Desktop

=== "Windows"

    1. Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
    2. Install and launch Docker Desktop
    3. Enable **WSL 2** if prompted
    4. Wait until the taskbar whale shows **Docker Desktop is running**

=== "macOS"

    1. Download **Docker Desktop for Mac** — **Apple Silicon** or **Intel** to match your Mac
    2. Drag Docker to Applications and launch it
    3. Wait until the menu-bar whale shows **Docker Desktop is running**

---

## Step 2 — Get the qClip project files

There is **no zip in the invite email** for the Windows installer path. For Docker you need the repo once:

- Reply to your invite email and ask for a clone/kit link, **or**
- Clone the private/public repo if you already have access

Example folders:

- Windows: `C:\qClip` or `D:\Projects\streamclip`
- macOS: `~/qClip` or `~/Projects/streamclip`

---

## Step 3 — Start the stack

=== "Windows"

    Open **PowerShell**, `cd` into the project folder, then:

    ```powershell
    .\scripts\start_local.ps1
    ```

    This checks Docker, creates `.env` if needed, runs `docker compose up -d --build`, migrates the DB, and runs `verify_stack.ps1`.

=== "macOS"

    ```bash
    cd ~/qClip   # adjust path
    cp .env.example .env
    docker compose up -d --build
    docker compose exec -T api alembic upgrade head
    ```

    Optional with [PowerShell Core](https://github.com/PowerShell/PowerShell): `pwsh -File ./scripts/start_local.ps1`

!!! note "First run"
    Docker downloads images (~2–5 GB). Allow 5–15 minutes.

---

## Step 4 — Verify you're ready

1. Open [http://localhost:3000](http://localhost:3000)
2. Go to **Settings → Get started** — you want **Ready**
3. Import your cohort key once, then activate:

```bash
docker compose exec -e PYTHONPATH=/app api python scripts/import_invite_license.py \
  --key SCPRO-XXXX-XXXX-XXXX-XXXX --tier admin --email you@example.com
```

Then paste the **same** key in **Settings → License**.

**Optional Docker health check:**

```bash
docker compose ps
curl -s http://localhost:8000/api/health
```

---

## Step 5 — Stop when done

```bash
docker compose down
```

Data stays in Docker volumes. Add `-v` only to wipe everything.

---

## Next steps

| Tutorial | What you'll do |
|----------|----------------|
| [First clip](../BETA_TESTER_QUICKSTART.md) | Creators — run a job (published) |
| [First job (deep-dive)](TUTORIAL_FIRST_JOB.md) | Operator walkthrough (repo only) |
| [GPU setup](TUTORIAL_GPU_SETUP.md) | NVIDIA on Windows Docker (repo only) |
| [Troubleshooting](TUTORIAL_TROUBLESHOOTING.md) | Top failures and fixes (published) |

*See also: [Beta quickstart](../BETA_TESTER_QUICKSTART.md) · [Known issues](../BETA_KNOWN_ISSUES.md)*
