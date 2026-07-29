# Zero-friction beta install — design

**Date:** 2026-07-28  
**Status:** Implemented in **v1.0.0-beta.6** (W1 docs + W2 seed + W3 secrets + W4 medium whisper). Historical design — do not treat version numbers below as current.  
**Trigger:** Beta tester feedback: "all I want is a link to download the installer."

---

## Problem

Getting a Phase 0 tester from invite email to a finished clip currently requires reading two documents, choosing between two install paths, and running a terminal command. The terminal command is impossible on the path we tell most people to use.

## Goal

One link. Install. Paste key. Clip and publish. No Docker, no terminal, no document reading.

## Non-goals

- CUDA/GPU packaging (see Deferred).
- macOS `.dmg` (needs a Mac host).
- EV code-signing certificate (purchase decision, tracked as O11).

---

## What already works

The Windows `.exe` is genuinely self-contained. This is the good news and it means the goal is mostly a matter of removing obstacles, not building a new install system.

- No Docker anywhere in `apps/desktop/`. The embedded runtime is SQLite + in-process queue + local storage (`config/desktop.yaml:13-25`).
- ffmpeg is bundled and resolved from `bin/ffmpeg/` (`core/ffmpeg_bins.py:38-63`).
- Migrations run automatically at sidecar boot (`desktop_sidecar/run.py:101-121`), so there is no setup step.
- No account is required to clip: `allow_anonymous: true` (`core/config.py:289`).
- `v1.0.0-beta.5` is published as Latest with `qClip-Setup-win-x64.exe` (487 MB), and the `releases/latest/download/...` URL already resolves to it.

## What blocks a painless install

Four defects, in priority order.

1. **A pasted license key cannot activate.** `backend/api/license.py:112-141` accepts a key only if its hash already exists in the local database, or if a Lemon Squeezy API key is configured (it is not, `core/config.py:308`). Every desktop install starts with an empty SQLite DB, so an emailed `SCPRO-` key returns "invalid key". The documented workaround, `scripts/import_invite_license.py`, is not shipped inside the installer and its usage assumes `docker compose exec`.
2. **Publishing is dead on desktop.** `distribution.token_encryption_key` defaults to `""` (`core/config.py:322`) and nothing generates one for desktop. OAuth token storage fails, so YouTube/TikTok publishing — the thing the Pro gate sells — cannot work.
3. **Entitlements are forgeable.** Desktop runs as `environment: development` (`core/config.py:387`) with `auth.secret_key = "CHANGE_ME_IN_PRODUCTION"` (`core/config.py:283`), and the sidecar never overrides it. Entitlement JWTs (`core/licensing.py:93`) are therefore signed with a publicly known constant, so anyone can mint an admin entitlement. This undermines a paid gate.
4. **First run silently downloads ~3 GB.** `whisper.model_size` defaults to `large-v3` (`core/config.py:26`) and `config/desktop.yaml` does not override it. On the CPU-only bundle this model is also too slow to be usable.

Plus documentation drift: the download page advertises `beta.4` while Latest is `beta.5`; it tells `.exe` users to "sign up or log in" when they need not; the quickstart tells everyone to "extract the beta `.zip` from your invite email" when no zip is attached and the `.exe` path has no zip; and the onboarding wizard still describes MinIO and Docker volumes (`web/components/onboarding/onboarding-wizard.tsx:98-106`).

---

## Design

Four independent workstreams. Each can ship and be verified alone.

### W1 — One link, one page

Collapse the tester-facing surface to a single page whose first screen is a download button.

- Rewrite `docs/BETA_DOWNLOAD.md` so the hero is one Windows button and exactly three steps: download, run, paste key. Everything else (requirements, troubleshooting, Docker) moves below the fold or into a separate advanced page.
- Point at `releases/latest/download/qClip-Setup-win-x64.exe` so the link never goes stale again, and correct the version banner to `beta.5`.
- Reframe the zip honestly: it is a Docker-self-host artifact, not something testers need. Remove it from the `.exe` path entirely.
- Remove the "sign up or log in" instruction; fix the onboarding storage step copy.
- Rewrite the invite email body in `scripts/send_beta_test_info_emails.py` to one link plus the key, deleting the `import_invite_license.py` line and the "extract the beta .zip" line.

**Unit boundary:** documentation and copy only, no runtime behavior.

### W2 — License activates from the UI

Two phases, as chosen: seed now, signed keys later.

**Phase A (now).** Ship a hash allowlist inside the installer and seed it at boot.

- New file `packaging/cohort/cohort_licenses.json`, shape `{"version": 1, "licenses": [{"key_hash": "<sha256>", "tier": "admin"}]}`. It contains only SHA-256 hashes and tiers — no keys, no emails. Hashes are one-way, so shipping them discloses nothing.
- New generator `scripts/build_cohort_seed.py --keys-csv <csv> --out <json>` so the file is reproducible from the operator's keys CSV and never hand-edited.
- New module `desktop_sidecar/seed_licenses.py` exposing `seed_bundled_licenses()`, called from `run.py` immediately after `run_migrations()`.
- Staged into the bundle via `datas` in `packaging/pyinstaller/streamclip-sidecar.spec`, following the existing `config/desktop.yaml` pattern at lines 29-34.

Seeding rules, chosen to be safe under repeat runs and upgrades:

- Idempotent: insert a row only when the hash is absent.
- Never overwrite an existing row's tier, and never resurrect a `revoked` row.
- A malformed or missing JSON file logs a warning and boots normally; it must never block startup.

**Phase B (later).** A self-verifying `SCPRO2-<payload>.<signature>` key format checked against a public key baked into the build, so new testers need no rebuild. Deliberately deferred: it would require reissuing the 8 keys we just told testers are valid.

**Unit boundary:** `seed_licenses.py` depends only on the repository layer and the bundled JSON. It does not touch the activation endpoint, which stays unchanged.

### W3 — Per-install secrets

New module `desktop_sidecar/install_secrets.py` exposing `ensure_install_secrets(data_dir)`.

- On first boot, generate and persist a `secrets.json` under `%LOCALAPPDATA%\StreamClip` containing a random 32-byte `auth_secret_key` and a Fernet `token_encryption_key`.
- Export them via `os.environ.setdefault` for `STREAMCLIP_AUTH__SECRET_KEY` and `STREAMCLIP_DISTRIBUTION__TOKEN_ENCRYPTION_KEY`, matching the existing convention in `configure_data_dirs` (`desktop_sidecar/run.py:76-80`) so explicit user env always wins.
- Must be called inside `configure_desktop_env` **before** `get_settings()` is first evaluated, otherwise the placeholder secret is already cached.

This fixes blockers 2 and 3 together, because both are the same missing-secret problem.

**Known upgrade effect:** existing installs signed entitlements with the old placeholder secret, so after upgrading, a previously activated machine must re-activate once. With 8 testers and 2 activations this is acceptable; the UI should present a re-activate prompt rather than a raw error.

### W4 — Fast first run

- Set `whisper.model_size: small` in `config/desktop.yaml`. This cuts the first-run download from roughly 3 GB to a few hundred MB, and on the CPU-only bundle `small` is the difference between usable and abandoned. `medium` is the fallback if transcript quality regresses noticeably.
- Surface the existing prefetch progress (`/api/health/models`, started at `desktop_sidecar/run.py:124`) on the loading screen so the wait is visible rather than a silent stall.

---

## Data flow (first run, after this work)

```
Install .exe
  → Electron spawns sidecar (apps/desktop/src/main.ts:25-27)
    → configure_desktop_env
       → ensure_install_secrets   (W3, new: before settings load)
       → configure_data_dirs
    → run_migrations
    → seed_bundled_licenses       (W2, new: after migrations)
    → start_model_prefetch        (W4: now 'small')
  → UI loads, user pastes SCPRO- key in Settings → License
    → POST /api/license/activate finds the seeded hash → issues entitlement JWT
      signed with the per-install secret
  → Pro unlocked; publishing works because the Fernet key exists
```

## Error handling

| Failure | Behavior |
|---|---|
| `cohort_licenses.json` missing or malformed | Warn, continue boot. Activation simply behaves as it does today. |
| Seed row already present | No-op. Never overwrite tier, never un-revoke. |
| `secrets.json` unreadable or corrupt | Regenerate, and log that re-activation is required. Never crash the sidecar. |
| Entitlement signed with the old placeholder secret | Verification fails; UI prompts re-activation instead of showing a raw error. |
| Model prefetch fails | Existing behavior: job falls back to on-demand download. |

## Testing

- **Unit (counts toward the ≥95% `backend` + `core` gate):** seed idempotency; tier is not downgraded; revoked rows are not resurrected; malformed JSON is tolerated; secrets persist across restarts and are not regenerated when present.
- **Desktop-marked (`@pytest.mark.desktop`, excluded from the gate):** `configure_desktop_env` ordering — secrets exported before settings load.
- **Manual, clean Windows VM:** install `.exe` → paste key → activate succeeds with no terminal → connect a platform → publish. This is the real acceptance test and the one that would have caught all four blockers.
- Existing `web/e2e` mock suite is unaffected.

---

## Resolved decisions

1. **Whisper size is `medium`.** Transcript quality wins over download size. Because `medium` is roughly 1.5 GB, the first-run download must be *honest and visible*: state the size up front and show live progress. A silent multi-GB pull is not acceptable — see W4.
2. **The Docker self-host path stays, unlinked.** Do not delete any Docker documentation. Remove it from the tester-facing flow and from site navigation so testers cannot stumble into it, but keep every page reachable by direct URL for operators. The primary download page presents exactly one obvious path: download the installer.
3. **Re-activation on upgrade is accepted.** The per-install secret is generated with no grandfathering of `CHANGE_ME_IN_PRODUCTION`. The two currently activated machines — Wellium and FJ — will need to re-paste their keys once after upgrading. The re-activation experience must be a clear, self-explanatory prompt, never a bare "invalid license" error.

## Deferred

- **GPU acceleration.** The bundle ships CPU-only torch (`requirements-desktop.txt:13-17`), so `cuda_available()` is False and NVENC is never probed (`core/gpu_profile.py:41-49,108-110`). Even on an RTX machine, clipping stays on CPU with libx264. Fixing this means shipping CUDA wheels and a much larger installer — a separate project, but it is the single biggest remaining "this feels slow" complaint.
- **SmartScreen.** Unsigned installer warns until an EV or Azure Trusted Signing certificate is purchased (O11). Mitigate with honest copy and a published checksum.
- **macOS `.dmg`.** Scaffolded; needs a Mac host.
