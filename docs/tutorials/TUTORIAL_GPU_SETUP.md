# Tutorial — GPU Setup

!!! warning "Not on the public docs site"
    Creators: see **[Known issues](../BETA_KNOWN_ISSUES.md)** for CPU vs GPU expectations. This page is an operator deep-dive kept in the repo only.

**Time:** ~15 minutes · **Prerequisite:** [Install](../BETA_DOWNLOAD.md#one-click-installers) or [Docker deep-dive](TUTORIAL_INSTALL.md)

qClip is **much faster** with **GPU acceleration on**. How you turn it on depends on how you installed:

| Install | Where to check | How to speed up |
|---------|----------------|-----------------|
| **Windows `.exe`** | **Settings → Get started** | Follow the in-app ready check; GPU is on when available on your hardware |
| **Docker (Windows + NVIDIA)** | **Settings → Get started** + steps below | Enable GPU in Docker Desktop, then use the `gpu` compose profile |
| **Docker (Mac)** | **Settings → Get started** | CPU is expected — use shorter sources or wait longer |

Plain rule: **GPU on = faster**. **CPU = always works**, just slower.

---

## Platform summary

| Platform | Beta path | Expected 1h VOD |
|----------|-----------|-----------------|
| **Windows + NVIDIA** | Docker + `gpu-worker` | ~20–25 min |
| **Windows CPU-only** | Docker default | ~60–90+ min |
| **macOS Docker** | CPU default | ~60–90+ min |
| **macOS DMG (future)** | MPS / VideoToolbox | TBD |

For timing expectations on your hardware, run a short test job and compare — see [Troubleshooting](TUTORIAL_TROUBLESHOOTING.md) if jobs are unexpectedly slow.

---

## Windows — one-click installer (`.exe`)

1. Launch qClip from the Start menu after install
2. Open **Settings → Get started** — wait for **Ready**
3. If processing is still slow on an NVIDIA PC, you may be on the CPU path; use **Help → GPU setup** in the app and reply to your invite email with your GPU model

Docker is **not** required for the `.exe` path.

---

## Windows — NVIDIA + Docker (beta stack)

### Step 1 — Hardware and drivers

1. Confirm an **NVIDIA GPU** (GTX 1060+ or RTX series recommended)
2. Install latest **Game Ready** or **Studio** drivers from [nvidia.com/drivers](https://www.nvidia.com/drivers)
3. Reboot if the installer requires it

### Step 2 — Enable GPU in Docker Desktop

1. Open **Docker Desktop → Settings → Resources**
2. Enable **GPU** / **Use GPU acceleration** (wording varies by Docker version)
3. Ensure your NVIDIA card appears in the list
4. Click **Apply & Restart**

### Step 3 — Start the GPU worker profile

From your qClip / streamclip project folder:

```powershell
docker compose --profile gpu up -d --build
```

For production compose:

```powershell
docker compose -f docker-compose.prod.yml --profile gpu up -d
```

Set on the **CPU worker** when using isolated GPU queue:

```bash
STREAMCLIP_WORKER_QUEUES=default
```

GPU tasks route to `gpu-worker`; LLM and HTTP tasks stay on the default worker.

### Step 4 — Verify GPU inside the worker

```powershell
docker compose exec worker nvidia-smi
# or, with gpu profile:
docker compose exec gpu-worker nvidia-smi
```

You should see your GPU name, driver version, and memory.

### Step 5 — Confirm in the app

Open **Settings → Get started**. Optional services (AI scoring) can be off — jobs still complete.

!!! warning "No GPU in container"
    If `nvidia-smi` fails inside the container, jobs still run on CPU — see [Troubleshooting](TUTORIAL_TROUBLESHOOTING.md).

---

## macOS — Docker CPU (beta default)

Apple Silicon and Intel Macs **do not expose NVIDIA/NVENC** inside Docker Desktop. This is expected.

### Step 1 — Give Docker more resources

1. **Docker Desktop → Settings → Resources**
2. Increase **CPUs** (≥4) and **Memory** (≥8 GB, 12+ GB better)
3. Apply and restart Docker

### Step 2 — Use Apple Silicon native images

When downloading Docker Desktop, pick **Apple Silicon** (not Intel/Rosetta) on M-series Macs.

### Step 3 — Start qClip (no GPU profile)

```bash
docker compose up -d
```

Do **not** use `--profile gpu` on Mac — there is no NVIDIA runtime.

### Step 4 — Set expectations

- Jobs complete on **CPU** — allow 60–90+ minutes for a 1-hour VOD
- Use shorter test sources during beta
- Fan noise and heat are normal under sustained encode

Confirm **Settings → Get started** shows **Ready** before your first job.

---

## macOS — Future DMG + MPS path

The one-click **`.dmg` installer is not public yet**. Builder notes:

- [macOS installer](../MACOS_INSTALLER.md) — unsigned DMG build script
- [ADR-001](../ADR-001-desktop-packaging.md) — embedded runtime design
- **MPS / VideoToolbox** encode paths are **in progress** (§5.1–5.2 in MASTER_TODO)

When the DMG ships, Apple Silicon will use **MPS** for ML and VideoToolbox for encode — faster than Docker CPU, not yet available to beta testers.

!!! note "Mac beta today"
    **Docker CPU is the supported path.** No Xcode or Apple Developer account required.

---

## Quick comparison after setup

Run the same ~10 min test clip on your hardware and note wall-clock time:

| Check | Windows GPU | Mac Docker |
|-------|-------------|------------|
| `nvidia-smi` in worker | ✅ | N/A |
| Job stages use GPU | transcribe + render fast | all CPU |
| 10 min source → clips | ~3–5 min | ~10–15 min |

Report timings via **Beta feedback** in the app header.

---

## Next steps

- [First clip](../BETA_TESTER_QUICKSTART.md) — run a timed test (published)
- [Troubleshooting](TUTORIAL_TROUBLESHOOTING.md) — GPU not detected (published)

---

*See also: [Beta quickstart](../BETA_TESTER_QUICKSTART.md) · [Known issues](../BETA_KNOWN_ISSUES.md)*
