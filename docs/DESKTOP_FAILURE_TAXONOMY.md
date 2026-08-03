# Desktop failure taxonomy (product-path root causes)

**Revision:** 1 (2026-07-31)
**Scope:** the Windows/macOS desktop installer — Electron shell + PyInstaller sidecar + SQLite + in-process worker + LocalStorage. This is the **product**. The Docker stack is dev/Pro only (see [ADR-001](ADR-001-desktop-packaging.md)).

## Why this doc exists

qClip "works perfectly locally" but breaks for other Windows users because the pivot to a desktop installer (ADR-001) left the **verification and documentation centered on Docker** while the *product* is the `.exe`. The bugs that actually shipped were **rudimentary packaging/runtime invariants**, not ML. This file is the single register of those failure classes: symptom, root cause, owning module, the regression test that guards it, and status.

Severity: **P0** = fresh install cannot reach first clip · **P1** = common, degrades trust · **P2** = edge/optional.

## Register

| ID | Class | Symptom (user sees) | Root cause | Owning module(s) | Guard test | Status |
|----|-------|---------------------|------------|------------------|------------|--------|
| **F1** | Writable path | White screen / license activation 500 | A runtime write path resolves under a read-only install prefix (`C:\Program Files`) | `Settings._writable_slots` / `ensure_dirs` / `verify_writable` ([core/config.py](../core/config.py) ~474–556); `configure_data_dirs` ([desktop_sidecar/run.py](../desktop_sidecar/run.py) ~63–92) | `tests/test_config.py::test_writable_slots_registry_is_complete`, `::test_verify_writable_reports_unwritable_slot`; **new** `tests/test_sidecar_packaging.py::test_run_server_exits_when_data_dirs_unwritable` | **Fixed + hardened** — registry complete; sidecar now `SystemExit(1)` on unwritable (was log-only, booted into guaranteed 500) |
| **F2** | Stale UI embed | New exe shows old UI | `static/ui` is baked **inside** the sidecar bundle; if staged before a UI rebuild the exe ships stale HTML | `scripts/stage_sidecar_for_electron.ps1` (stale-UI guard, `STREAMCLIP_ALLOW_STALE_UI=1` override); spec datas ([packaging/pyinstaller/streamclip-sidecar.spec](../packaging/pyinstaller/streamclip-sidecar.spec) ~36–39) | build-script guard (manual) | Guarded; still human-order-sensitive → clean-VM gate covers |
| **F3** | Version drift | Auto-update points at wrong version | `apps/desktop/package.json` version vs `latest.yml` mismatch | `scripts/publish_desktop_release.ps1` (asserts version match) | publish-script assertion | Guarded |
| **F4** | Sidecar death / boot fail | Blank window or "engine did not start" | Sidecar crashes/exits before health; or missing exe | Electron supervise + `failure-reason.ts` (extracted pure logic) → `startup-error.html`; sidecar boot failures propagate non-zero ([desktop_sidecar/run.py](../desktop_sidecar/run.py) `main`→`run_server`) | `apps/desktop/src/failure-reason.test.ts` (6, `npm test`); `tests/test_sidecar_packaging.py::test_run_server_propagates_boot_failure_nonzero` | **Fixed + proven** — Python side exits non-zero on boot failure; Electron reason is never blank; splash + error page + Open-engine-log + Retry/Restart |
| **F5** | SQLite migrate | Boot fail after update | Alembic migration incompatible with SQLite, or upgrade-from-beta.N path untested | `run_migrations` at boot ([desktop_sidecar/run.py](../desktop_sidecar/run.py) ~114–135); portable types ([backend/db/types.py](../backend/db/types.py)) | `tests/test_sqlite_profile.py`, `tests/test_sidecar_packaging.py::test_run_migrations_calls_alembic`; **`scripts/verify_desktop_upgrade.ps1`** (old-rev DB → boot → data preserved) | **Guarded** — upgrade simulation passes (0012→head, data + licenses preserved); manual matrix in [DESKTOP_UPGRADE_MATRIX.md](DESKTOP_UPGRADE_MATRIX.md) |
| **F6** | First-run models | Stuck on "warming models" | Model download fails (disk full, network, AV quarantine) with no clear surface | `core/model_prefetch.py` (`classify_failure`/`failure_hint`/`retry_prefetch`); `/api/health/models` (+`failed`/`hint`) + `POST /api/health/models/retry`; `ModelWarmupBanner` failed state + Retry | `tests/test_model_prefetch.py` (classify/hint/retry/endpoint — 17 tests) | **Fixed** — failures now show an actionable cause (disk/network/permission) + Retry instead of a silent spinner |
| **F7** | GPU false confidence | ffmpeg crash or silent slow CPU | NVENC/CUDA requested but absent | `core/gpu_profile.py` (`effective_export_codec`, `effective_whisper_device`, `apply_gpu_env_defaults`) | `tests/` gpu profile cases | **Good** — upgrades when present, downgrades when absent; CPU default in `config/desktop.yaml` |
| **F8** | In-process Beat | "Scheduled publish never fired" | Beat runs only while the app is open (single-machine reality) | `InProcessWorker._beat_loop` ([core/inprocess_worker.py](../core/inprocess_worker.py) ~91–131) | `tests/` inprocess beat | **By design** — documented in BETA_KNOWN_ISSUES; product decision, not a bug |
| **F9** | Unsigned trust | SmartScreen "unrecognized app" | No EV Authenticode cert yet | `apps/desktop/package.json` win/nsis; `publish_desktop_release.ps1 -RequireSigned` (validates Authenticode Valid); `verify_desktop_release.ps1 -RequireSigning`; [DESKTOP_SIGNING.md](DESKTOP_SIGNING.md) | signing preflight | **Tooling done — blocked on operator cert purchase (O11).** Gate + runbook turnkey; workaround documented in BETA_KNOWN_ISSUES |
| **F10** | Dual-runtime drift | Feature works in Docker, dies in exe | A code path assumes Celery/Redis instead of routing through the seam | `core/task_dispatch.py`, `core/task_runner.py`, `core/progress_bus.py`; `_inprocess_enabled` checks | `tests/test_sqlite_profile.py`, `verify_inprocess.ps1`; **`scripts/verify_desktop_coverage.ps1`** (dedicated seam gate, no waiver) | **Guarded** — seam coverage gate at 85% floor (actual **91%**); the Docker `-m "not desktop"` waiver no longer hides the seam |
| **F11** | Doc/todo rot | Agents "close" Docker items while the exe burns | TDD/CLEAN_VM/gates treat Docker as canonical | `docs/TECHNICAL_DESIGN.md`, `docs/CLEAN_VM_VERIFY.md`, `docs/MASTER_TODO.md §3.8/§8` | process gate | **Fixing this revision** — TDD Rev 5 desktop-primary + clean-desktop-VM gate |
| **F13** | **Feedback black hole** | Tester submits Help → Report a bug / beta feedback; **operator never receives it** (UI now says local-only) | Both notification channels are **env-only** and unset on desktop: `ops_webhook_status()` → `skipped_unconfigured` without `OPS_WEBHOOK_URL`; `bug_report_email_status()` same without SMTP/`BUG_REPORT_TO`. `_queue_support_notifications` dispatches nothing; row stays in tester **local SQLite**. Operator reader targets Docker Postgres | `backend/api/support.py`, `core/notify/*`, `api/support-ingest.py`, Electron `OPS_WEBHOOK_URL` → henna | toasts honest; packaged smoke `ops_notification=queued` | **CLOSED 2026-08-03** — henna collector live (`GET/POST …/api/support-ingest` email delivered); Vercel `SMTP_*` + `BUG_REPORT_TO` set; packaged Electron wires collector URL (MASTER §4.22) |
| **F12** | Frozen env not applied | Packaged exe silently uses `large-v3` + optical flow (slow) | `config/desktop.yaml` overrides must land before `backend.main` import when frozen | env-before-import ([desktop_sidecar/run.py](../desktop_sidecar/run.py) ~158–161); `sys._MEIPASS` root ([desktop_sidecar/run.py](../desktop_sidecar/run.py) ~22–35) | `tests/test_sidecar_packaging.py::test_configure_desktop_env_sets_config` | Guarded; **desktop perf column should measure the frozen exe to confirm** |

## What the audit confirmed about severity

The codebase is **mature**. Of 12 classes, most are already fixed or guarded in code. The **actionable residue** is small and mostly non-ML:

1. **F1** — hardened this revision (log-only → fatal). This was the highest-value one-line class of crash.
2. **F11** — the meta-cause. Fixed by re-centering docs + adding the product gate (below).
3. **F5 upgrade matrix**, **F6 first-run failure copy**, **F10 coverage waiver** — the remaining real work, all small.
4. **F9 EV signing** — money/ops, not code.

## The regression rule (anti-recurrence)

- Every **new writable path** → add to `_writable_slots` (enforced by `test_writable_slots_registry_is_complete`).
- Every **new task** → dispatch via `core/task_dispatch.py`, never `.delay()` directly (guards F10).
- Every **new desktop failure** → add a row here + a guard test, and lift the module out of the `-m "not desktop"` coverage waiver.
- The **clean-desktop-VM gate** ([CLEAN_DESKTOP_VM_VERIFY.md](CLEAN_DESKTOP_VM_VERIFY.md)) — not `verify_coverage.ps1` alone — is the ship blocker for the product.
