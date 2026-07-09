# Tutorial — GPU Setup

**Time:** ~15 minutes · **Prerequisite:** [Install tutorial](TUTORIAL_INSTALL.md)

StreamClip is **much faster** with GPU acceleration. Setup differs by platform: **NVIDIA + Docker** on Windows, **CPU default** on macOS Docker beta, with a future **DMG + MPS** path on Apple Silicon.

---

## Platform summary

| Platform | Beta path | Expected 1h VOD |
|----------|-----------|-----------------|
| **Windows + NVIDIA** | Docker + `gpu-worker` | ~20–25 min |
| **Windows CPU-only** | Docker default | ~60–90+ min |
| **macOS Docker** | CPU default | ~60–90+ min |
| **macOS DMG (future)** | MPS / VideoToolbox | TBD |

See [Performance](../PERFORMANCE.md) for SLIs.

---

## Windows — NVIDIA + Docker

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

From your StreamClip folder:

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

### Step 5 — Confirm NVENC in logs

Run a short test job ([First job](TUTORIAL_FIRST_JOB.md)). Worker logs should show `nvenc` or `cuda` when GPU is active.

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

### Step 3 — Start the stack (no GPU profile)

```bash
docker compose up -d
```

Do **not** use `--profile gpu` on Mac — there is no NVIDIA runtime.

### Step 4 — Set expectations

- Jobs complete on **CPU** — allow 60–90+ minutes for a 1-hour VOD
- Use shorter test sources during beta
- Fan noise and heat are normal under sustained encode

Optional verify:

```bash
docker compose ps
curl -s http://localhost:8000/api/health/stack
```

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

- [First job](TUTORIAL_FIRST_JOB.md) — run a timed test
- [Troubleshooting](TUTORIAL_TROUBLESHOOTING.md) — GPU not detected

---

*See also: [Beta quickstart](../BETA_TESTER_QUICKSTART.md) · [Known issues](../BETA_KNOWN_ISSUES.md)*
