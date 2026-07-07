# Desktop packaging (ADR-001 §4.6–4.7)

## Sidecar (PyInstaller)

| Path | Purpose |
|------|---------|
| `desktop_sidecar/run.py` | Entry: migrations + uvicorn (workers=1, in-process queue) |
| `packaging/pyinstaller/streamclip-sidecar.spec` | One-dir **full ML bundle** (torch CPU, faster-whisper, ultralytics, mediapipe, librosa) |
| `scripts/build_sidecar.ps1` | Tests + full PyInstaller build with size report |
| `scripts/verify_sidecar_exe.ps1` | Smoke test the built exe (boot → health → migrations) |
| `scripts/run_desktop_sidecar.ps1` | Dev sidecar without PyInstaller |
| `requirements-desktop.txt` | CPU-only torch wheel profile for the build venv |

```powershell
# Build venv should use CPU-only torch (2 GB smaller than CUDA):
pip install -r requirements-desktop.txt -r requirements-packaging.txt

# Full build (~1.1 GB one-dir output, several minutes)
.\scripts\build_sidecar.ps1

# Smoke test the bundle (temp data dir, prefetch skipped)
.\scripts\verify_sidecar_exe.ps1

# Scaffold tests only (skip PyInstaller)
$env:STREAMCLIP_SKIP_PYINSTALLER = "1"; .\scripts\build_sidecar.ps1

# API-only lite bundle (no ML stack — fast packaging smoke)
$env:STREAMCLIP_LITE = "1"; .\scripts\build_sidecar.ps1
```

Bundled output: `dist/streamclip-sidecar/streamclip-sidecar.exe` (Windows, ~1.1 GB one-dir).
Model weights are **not** bundled — they download on first run (§4.8 prefetch,
progress at `/api/health/models`). Bundled resources (config, alembic, static UI,
ffmpeg if present in `bin/ffmpeg/`) resolve via `sys._MEIPASS` (`_internal/`).

### Data directory (§4.18)

Frozen (PyInstaller) builds keep user data out of the install dir. On startup
`configure_desktop_env()` resolves a per-user data dir and points env overrides
into it (SQLite DB, `storage/`, `workspace/`, `cache/`), creating directories
as needed. `config/desktop.yaml` keeps its dev-relative defaults.

| Scenario | Data dir |
|----------|----------|
| `STREAMCLIP_DESKTOP_DATA_DIR` set (any mode) | that path |
| Frozen, Windows | `%LOCALAPPDATA%\StreamClip` |
| Frozen, no `LOCALAPPDATA` | `~/.streamclip` |
| Dev (not frozen, no override) | none — dev-relative `./workspace/` |

Explicit `STREAMCLIP_DATABASE__URL` / `STREAMCLIP_STORAGE__LOCAL_ROOT` /
`STREAMCLIP_WORKSPACE_DIR` / `STREAMCLIP_CACHE_DIR` env vars always win
(overrides use `setdefault`).

## Static UI (§4.7 + §4.7a)

| Path | Purpose |
|------|---------|
| `backend/static_ui.py` | Mount `static/ui/` at `/` with SPA fallback |
| `web/next.config.mjs` | `NEXT_STATIC_EXPORT=1` → `output: "export"` |
| `web/lib/api/actions/` | Client-side API mutations (replaces Server Actions) |
| `web/lib/auth/client-session.ts` | localStorage + cookie mirror for auth/SSE |
| `scripts/build_desktop_ui.ps1` | Stash `middleware.ts`, build, copy `web/out` → `static/ui` |

Enable in `config/desktop.yaml`:

```yaml
web:
  serve_static: true
  static_dir: static/ui
```

Build:

```powershell
.\scripts\build_desktop_ui.ps1
```

**Dev note:** `middleware.ts` is disabled during static export builds (onboarding redirect). Docker/Next dev still uses `middleware.ts` normally.

## Electron (§4.13)

`apps/desktop` spawns the Python sidecar and opens a `BrowserWindow` to `http://127.0.0.1:8765/`.

| Dev | `python -m desktop_sidecar` via `npm start` in `apps/desktop` |
| Prod | `streamclip-sidecar.exe` beside Electron resources (`resources/sidecar/`) |

Preload exposes `window.streamclip.sidecar.{start,stop,health}` and `window.streamclip.version()`.

Tray uses `apps/desktop/assets/tray-icon.png` when present; otherwise a built-in 16×16 fallback.
