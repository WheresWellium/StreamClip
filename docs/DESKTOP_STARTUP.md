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

| Platform | App data (DB, workspace) | Boot diagnostics |
|----------|--------------------------|------------------|
| Windows | `%LOCALAPPDATA%\qClip\` (reuses `%LOCALAPPDATA%\StreamClip\` if that folder already exists) | Electron `[boot]` in process console; sidecar stdio is discarded in packaged builds |
| macOS | `~/Library/Application Support/qClip/` | same |
| Linux / portable | `~/.qclip` (legacy `~/.streamclip` if present) | same |

For Docker beta, use `docker compose logs` (see `BETA_TESTER_QUICKSTART.md`). Packaged desktop does not yet write a rotating sidecar log file — capture job id + in-app bug report when escalating.

Regression: fail when splash is not shown before sidecar wait, or when the main window is exclusive-fullscreen instead of maximized/resizable.

See also `docs/PERFORMANCE.md` for pipeline SLIs (ingest → clip render).
