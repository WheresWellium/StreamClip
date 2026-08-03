# Desktop upgrade matrix (F5)

**Revision:** 2 (2026-08-03)
**Purpose:** prove that installing a new build **over an existing one** preserves the user's data (jobs, clips, license) and applies SQLite migrations cleanly. This guards taxonomy class **F5** (SQLite migrate / boot fail after update) — the failure a returning tester hits, distinct from the fresh-install path in [CLEAN_DESKTOP_VM_VERIFY.md](CLEAN_DESKTOP_VM_VERIFY.md).

## Why upgrades are a distinct risk

A fresh install runs `alembic upgrade head` against an empty SQLite DB. An **upgrade** runs it against a DB created by an older build — so every migration between the two versions must apply in order, on SQLite, without Postgres-only DDL. The relevant machinery already exists and is reused, not rebuilt:

- Migrations run at every sidecar boot: `run_migrations()` → `alembic upgrade head` ([desktop_sidecar/run.py](../desktop_sidecar/run.py) ~114–135).
- Portable DDL types keep migrations SQLite-safe ([backend/db/types.py](../backend/db/types.py)); migration `0014_sqlite_timestamp_defaults` replaced Postgres-only `now()` defaults.
- Data lives outside the install dir (`%LOCALAPPDATA%\StreamClip`), so an installer overwrite never touches the DB/storage.
- Licenses are re-seeded idempotently at boot ([desktop_sidecar/seed_licenses.py](../desktop_sidecar/seed_licenses.py)); user-activated keys persist in the DB.

## Support window

Test the upgrade from **each still-in-the-wild beta** to the shipping build. As of 2026-08-03: **beta.5–beta.23 → beta.24** (alembic head still `0014` since beta.7).

| From | To | Migrations applied | License | Data (jobs/clips) | Result |
|------|----|--------------------|---------|-------------------|--------|
| beta.5 | beta.24 | 0012 → 0014 (timestamp defaults) | persists, no re-entry | preserved | ☐ verify |
| beta.6 | beta.24 | 0014 (if not already) | persists | preserved | ☐ verify |
| beta.7–beta.23 | beta.24 | none (already on 0014) | persists | preserved | ☐ verify |
| fresh | beta.24 | 0001 → 0014 (all) | activate once | n/a | covered by clean-VM gate |

*(Fill the result column per release. If any cell fails, file an F5 row in [DESKTOP_FAILURE_TAXONOMY.md](DESKTOP_FAILURE_TAXONOMY.md) with the migration id and the alembic error.)*

## Manual upgrade test (per shipping build)

Run on a machine (or VM) that already has the previous beta installed **with real data**:

1. On the **old** build: create at least one job that reaches `done` with a clip; activate a license key. Note the `job_id`.
2. Fully quit qClip (tray → Quit; confirm no `qClip` / `streamclip-sidecar` processes remain).
3. Install the **new** build over it (default location; do **not** uninstall first — that is a separate clean path).
4. Launch. Confirm:
   - No white screen; sidecar becomes healthy.
   - Engine log shows `sidecar_migrations_applied` with the new migrations, no `sidecar_migrations_failed`.
   - The prior job/clip from step 1 is still listed and the clip still plays.
   - License still shows active — **no re-entry required**.
5. Create a new job on the new build → reaches `done`.

## Automated pre-flight (upgrade simulation)

`scripts/verify_desktop_upgrade.ps1` simulates the DB half of the upgrade without a full install: it seeds a SQLite DB at an **older migration revision**, then boots the sidecar (which runs `upgrade head`) against that same data dir and asserts health + that the pre-existing rows survive. Run before shipping:

```powershell
.\scripts\verify_desktop_upgrade.ps1
```

## Pass criteria

| Check | Required |
|-------|----------|
| `verify_desktop_upgrade.ps1` (DB simulation) | Yes |
| Manual beta.N → current, data preserved | Yes for each in-the-wild beta |
| License persists without re-entry | Yes |
| No `sidecar_migrations_failed` in engine log | Yes |

## Sign-off

```
Desktop upgrade matrix (F5)
From build: __________  To build: __________
verify_desktop_upgrade.ps1: PASS / FAIL
Data preserved (job_id ______): PASS / FAIL
License persisted (no re-entry): PASS / FAIL
Migrations clean (no failed): PASS / FAIL
Tester: __________  Date (UTC): __________
```
