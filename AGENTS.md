# qClip agent memory

Durable facts and preferences live here so long chats can summarize safely.
Update via `agents-memory-updater` or when the user corrects standing behavior.

## Learned User Preferences

- Prefer exact file paths and line numbers when citing code.
- Minimize context bloat: trim user rules, disable unused MCP/plugins, use subagents for exploration.
- Do not commit unless explicitly asked; use `gh` for GitHub PR/check work.
- After shipping user-facing web/auth changes to `master`, always build and publish a new Windows desktop installer (`scripts/publish_desktop_release.ps1`) and bump `docs/BETA_DOWNLOAD.md`.
- Coverage gate is authoritative via `scripts/verify_coverage.ps1` (Docker, `-m "not desktop"`).
- Phase 0 beta invites require both `verify_coverage.ps1` (≥95%) and `verify_stack.ps1` passing.

## Learned Workspace Facts

- **Product brand is qClip** (user-facing). Repo folder remains `streamclip`; technical env prefix `STREAMCLIP_*`, GitHub repo `WheresWellium/StreamClip`, license prefix `SCPRO-`, cookies `streamclip_*` unchanged until a migration pass.
- **Canonical repo root is `D:\Projects\streamclip` only** (migrated off `C:\Users\locat\Projects\streamclip`). Never open, edit, or resolve paths against the old C: tree — it is a hollow stale skeleton (no `.git`). Cursor project id: `d-Projects-streamclip`. Balance report: `tmp/drive-migration-balance.txt`.
- qClip is GPU-bound; hot path is ingest → transcribe → highlights → virality → clip render (`docs/PERFORMANCE.md`).
- Canonical coverage scope: `backend` + `core`; desktop tests excluded with `@pytest.mark.desktop`.
- `docs/MASTER_TODO.md` §3.10 defines coverage truth; §3.5 gate is **GREEN at 95.01%** (2026-07-07). Phase 0 invites now block only on §3.8 (clean-VM `verify_stack.ps1`).
- Never wrap `verify_coverage.ps1`/`verify_stack.ps1` with `2>&1 | Tee-Object` in PowerShell — throws a spurious `NativeCommandError` on normal `docker compose build` stderr output.
- Rolling session truth for active work: `docs/SESSION_STATE.md` (read after summarization).
- Parallel chats: one branch per task; acquire `docs/.agent-lock.json` before protected paths (`docs/AGENT_COORDINATION.md`).
- Agent transcripts: `~/.cursor/projects/d-Projects-streamclip/agent-transcripts/<chat-id>/*.jsonl` (grep, do not read linearly). Legacy folder `c-Users-locat-Projects-streamclip` is historical only.
- **Desktop is the product (2026-07-31 mastery audit):** the Windows/macOS **installer** (Electron + PyInstaller sidecar, SQLite, in-process worker, LocalStorage) is canonical for design/tests/gates. Docker compose is dev-only + the backend for a future managed-cloud/Pro SKU — never handed to end users (raw `docker compose`/CLI is rejected as a product). Truth: `docs/TECHNICAL_DESIGN.md` Rev 5 (desktop-primary; Docker → Appendix D), `docs/DESKTOP_FAILURE_TAXONOMY.md` (F1–F12), `docs/CLEAN_DESKTOP_VM_VERIFY.md`, `docs/DESKTOP_COHORT_EXIT.md`. **Turnkey pre-ship = `scripts/verify_desktop_release.ps1`** (coverage F10 + upgrade F5 + clean-boot F1/F12 + signing readiness); product exit = that + clean-VM install→first-clip + cohort numbers (MASTER §8.16d: crash-free >98% / install→first-clip <45m). Architecture decision: **harden the shared `core/`, do NOT rewrite**. Finish-line scope lock: FS-3 + roadmap deferred post-launch.
- **Two runtimes, one core:** desktop vs Docker differ ONLY by `queue.backend` (inprocess|celery), `database.url` (sqlite|postgres), `storage.backend` (local|minio). Any code assuming Celery/Redis directly is a drift bug — route through `core/task_dispatch.py`/`task_runner.py`; progress via `core/progress_bus.py` in desktop mode.
- **Sidecar fails fast on unwritable dirs:** `desktop_sidecar/run.py` `run_server` calls `verify_writable()` and `SystemExit(1)`s with an actionable message (was log-only → guaranteed 500/white screen). Electron surfaces it on `startup-error.html`.
- **Writable-path invariant (desktop):** every runtime path that gets written must be registered in `Settings._writable_slots()` (`core/config.py`). That registry is the single source of truth — `ensure_dirs()` relocates unwritable ones off read-only prefixes (Program Files) and `verify_writable()` fail-fasts at sidecar start. Never add ad-hoc relative write paths; add a slot. Enforced by `tests/test_config.py::test_writable_slots_registry_is_complete`. This class of bug caused the white screen (`output`) and the license 500 (`license_file`).
- **Desktop build stale-artifact guards:** `static/ui` is embedded INSIDE the PyInstaller sidecar bundle, so `stage_sidecar_for_electron.ps1` fails if `static/ui` is newer than the sidecar exe (override: `STREAMCLIP_ALLOW_STALE_UI=1`). `publish_desktop_release.ps1` derives version from `apps/desktop/package.json` and asserts it matches `latest.yml` (prevents auto-update drift). `build_desktop_ui.ps1` restores the middleware/`app/api` stash in a `finally`. electron-builder `afterPack` hook `apps/desktop/build/validate-sidecar.js` fails the build if the packaged app has no engine binary. PyInstaller spec aborts if a **critical** ML pkg (`torch`/`ctranslate2`/`faster_whisper`) fails `collect_all` (optional ones only warn). `linux` target removed (no sidecar staging). Keep build scripts ASCII-only (PowerShell mis-tokenizes em-dashes/`<>`).
