# ADR-001 — Windows desktop packaging: embedded runtime, not Docker

**Status:** Accepted (2026-07-07)
**Date:** 2026-07-02
**Decides:** MASTER_TODO 4.0 · **Unblocks:** 4.1–4.13, §5 (macOS)

## Context

We want to ship qClip as a Windows desktop executable for end users, with a
macOS port to follow. The current `apps/desktop` Electron shell is a *Docker
launcher*: it requires Docker Desktop and `docker-compose.prod.yml`, which pulls
`ghcr.io/streamclip/*` images that do not exist. That is not distributable to
non-technical creators.

The server stack today: FastAPI + Celery (Redis broker) + Postgres + MinIO +
optional Ollama, with GPU work (Whisper via CTranslate2, YOLO11 via torch,
NVENC via ffmpeg) on a dedicated queue.

## Decision

**Embedded runtime.** One installed app, no Docker, no external services:

| Server component | Desktop replacement | MASTER_TODO |
|---|---|---|
| Postgres | SQLite via `aiosqlite` (same SQLAlchemy models; audit Alembic for Postgres-only DDL) | 4.1 |
| Celery + Redis | **In-process worker** behind the existing task interface (thread pool for CPU/IO, single-slot executor for GPU stages to mirror the `gpu` queue) | 4.2 |
| Redis pub/sub (SSE progress) | In-process event bus feeding the same SSE endpoints | 4.2 |
| MinIO | Existing `LocalStorage` backend; workspace under `%LOCALAPPDATA%\JetStream` | 4.3, 4.8 |
| Ollama | Optional: user-supplied OpenAI/Anthropic key or local Ollama URL; virality already degrades to score 0 | 4.4 |
| ffmpeg on PATH | Bundled `ffmpeg.exe`/`ffprobe.exe` resolved relative to the app dir | 4.5 |
| Python in container | PyInstaller one-dir build of FastAPI + worker as a **sidecar process**; UI shell (keep Electron; Tauri optional later) spawns and supervises it | 4.6, 4.7 |
| Next.js server | `next build` static export served by the FastAPI sidecar (server actions replaced by direct API calls where needed) | 4.7 |

### Why not Docker-in-desktop

- Docker Desktop is a ~1.5 GB dependency with its own installer, licensing
  terms for larger orgs, WSL2 requirement, and admin rights — a support
  nightmare for the target audience (streamers, not devops).
- GPU passthrough (NVENC/CUDA) through Docker on Windows is fragile.
- Cold start is minutes (pull + compose up) vs seconds for a native sidecar.
- 4.2's queue options (a) Memurai and (c) huey both add moving parts;
  Memurai is Windows-only, which §5.6 flags as a macOS blocker. The
  in-process worker (option b) is the only choice that works unchanged on
  both platforms.

### Consequences / risks

- **Bundle size (biggest risk):** torch + CTranslate2 + models push a naive
  bundle to multi-GB. Mitigations, in order: CPU-only torch wheel by default,
  ONNX export for YOLO11, and first-run download of Whisper/YOLO weights with
  progress UI (4.8) instead of shipping them.
- **Single-machine concurrency:** the in-process worker caps parallelism at
  what one desktop can do. This matches reality (one GPU) and mirrors the
  performance rule "GPU tasks on the gpu queue only" — the single-slot GPU
  executor is that rule, in-process.
- **Migrations:** Alembic must run at app start against SQLite; JSONB and
  server-default DDL need portable variants (4.1). New migrations must be
  written Postgres+SQLite compatible from now on.
- **Two runtimes to test:** compose (self-hosted) and embedded (desktop).
  The task-interface seam keeps divergence to config: `queue.backend =
  celery|inprocess`, `database.url`, `storage.backend`.
- The server/self-hosted Docker path is unaffected; nothing is removed.

## Implementation order (maps to MASTER_TODO §4)

1. 4.2 in-process worker + progress bus (the seam everything else depends on)
2. 4.1 SQLite profile + migration audit
3. 4.5 bundled ffmpeg, 4.3 storage verification
4. 4.6 PyInstaller sidecar, 4.7 static web UI in shell
5. 4.8 first-run model downloads, 4.12 license activation UX
6. 4.13 Electron shell fixes, 4.10 installer + signing
7. 4.9 Windows-isms audit, 4.11 GPU detection with CPU-safe default

Windows signing operator source of truth: `packaging/installer/RELEASE_CHECKLIST.md`
(EV Authenticode first signed release) and `packaging/installer/README.md`
(installer implementation notes).

## Alternatives considered

- **Docker-in-desktop (keep current shell):** rejected — see above.
- **Tauri instead of Electron:** smaller shell, but the Python sidecar
  dominates bundle size either way; Electron shell already exists (4.13 fixes
  are cheaper than a rewrite). Revisit for macOS if Electron signing becomes
  painful.
- **huey/SQLite queue:** still a second process to supervise and a polling
  latency cost; the in-process worker is simpler and satisfies §5.6.
- **Rewrite pipeline in Node/Rust:** the ML stack (faster-whisper, ultralytics,
  librosa) is Python-native; a rewrite is out of scope.
