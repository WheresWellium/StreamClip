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

Regression: fail a desktop smoke when splash is not shown before sidecar wait,
or when the main window is exclusive-fullscreen instead of maximized/resizable.

See also `docs/PERFORMANCE.md` for pipeline SLIs (ingest → clip render).
