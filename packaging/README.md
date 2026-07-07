# Desktop packaging (ADR-001 §4.6–4.7)

## Sidecar (PyInstaller)

| Path | Purpose |
|------|---------|
| `desktop_sidecar/run.py` | Entry: migrations + uvicorn (workers=1, in-process queue) |
| `packaging/pyinstaller/streamclip-sidecar.spec` | One-dir bundle scaffold |
| `scripts/build_sidecar.ps1` | Test scaffold; optional full PyInstaller build |
| `scripts/run_desktop_sidecar.ps1` | Dev sidecar without PyInstaller |

```powershell
# Dev sidecar (SQLite + inprocess + static UI placeholder)
.\scripts\run_desktop_sidecar.ps1

# Scaffold tests only (skip multi-GB PyInstaller)
$env:STREAMCLIP_SKIP_PYINSTALLER = "1"
.\scripts\build_sidecar.ps1
```

Bundled output: `dist/streamclip-sidecar/streamclip-sidecar.exe` (Windows).

Set `STREAMCLIP_APP_ROOT` to the install dir so `bin/ffmpeg/`, `config/desktop.yaml`, and DB paths resolve.

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
