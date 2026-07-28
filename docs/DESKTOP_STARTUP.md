# Desktop startup budgets (qClip)

Measured on the Electron shell (`apps/desktop`). Timings are logged as
`[boot] <phase> +<ms>` from process ready.

| Phase | Meaning | Target (warm) | Target (cold) |
|-------|---------|---------------|---------------|
| `spawn` | `app.whenReady` | baseline | baseline |
| `splash` | Splash window visible | < 500 ms | < 1.5 s |
| `sidecar_start` | Local engine process spawned | < 200 ms after splash | < 500 ms |
| `sidecar_ready` | `/api/health` OK | < 8 s | < 45 s |
| `first_paint` | Main window loaded UI | < 10 s | < 60 s |
| `updater` | Deferred auto-update check | after first paint (+8 s) | same |

## Smoke checklist (Windows)

1. Launch installer / `npm start` → splash shows **qClip** immediately (never a blank wait).
2. Main window is **maximized**, resizable, no File/Edit/View menu bar.
3. Onboarding health step shows device recommendation; storage step shows **Saved on this device** path.
4. Settings → Get started shows the same device + storage cards.
5. Activate a Pro/Studio key → License panel lists `studio` and `publisher` capabilities.
6. Console/`[boot]` lines present for splash → sidecar_ready → first_paint.

## Where data and logs live

| Platform | App data (DB, workspace) | Logs |
|----------|--------------------------|------|
| Windows | `%LOCALAPPDATA%\qClip\` (reuses `%LOCALAPPDATA%\StreamClip\` if that folder already exists) | `%LOCALAPPDATA%\qClip\logs\` — `sidecar.log`, `electron.log` (plus `[boot]` lines in process console when launched from a terminal) |
| macOS | `~/Library/Application Support/qClip/` | `~/Library/Application Support/qClip/logs/` — `sidecar.log`, `electron.log` |
| Linux / portable | `~/.qclip` (legacy `~/.streamclip` if present) | `~/.qclip/logs/` — same filenames |

For Docker beta, use `docker compose logs` (see `BETA_TESTER_QUICKSTART.md`). For packaged desktop escalations, attach `sidecar.log` + `electron.log` with the job id / in-app bug report. Human install checklist: [HUMAN_DESKTOP_SMOKE.md](HUMAN_DESKTOP_SMOKE.md).

Regression: fail when splash is not shown before sidecar wait, or when the main window is exclusive-fullscreen instead of maximized/resizable.

See also `docs/PERFORMANCE.md` for pipeline SLIs (ingest → clip render).
