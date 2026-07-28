# qClip — Beta Known Issues

**Audience:** Phase 0–2 beta testers · **Owner:** core team  
**Last updated:** 2026-07-28  
**Update:** when shipping a beta wave or closing a blocker  
**Go-live / exit:** [Beta test plan §4.5 exit criteria](BETA_TESTER_PLAN.md#45-exit-criteria-phase-1) · evidence pack [BETA_COHORT_EXIT.md](BETA_COHORT_EXIT.md)

---

## Open issues (P1)

| Issue | Cause | Workaround | Affected |
|-------|-------|------------|----------|
| **Desktop: "Link jobs" returns Internal Server Error** | SQLite `local_devices` used Postgres `now()` default — **fixed in beta.6 branch** (`0014` migration + repo hardening) | **beta.5 users:** click **Skip** until beta.6 ships | Windows desktop `.exe` (SQLite) only |
| **Desktop: pasted SCPRO key fails activation** | Empty SQLite had no seeded license hashes — **fixed in beta.6 branch** (bundled cohort hash seed at boot) | **beta.5:** run `import_invite_license.py` once, or wait for beta.6 | Windows desktop `.exe` cohort |
| **Desktop: YouTube publish / OAuth fails** | Missing per-install Fernet + auth secrets — **fixed in beta.6 branch** (`install_secrets.py`) | **beta.5:** set env vars manually. **Upgrade to beta.6:** re-paste license once (expected) | Windows desktop `.exe` |

---

## Platform limits (by design for beta)

| Area | Behavior |
|------|----------|
| TikTok | **Off by default** (`TIKTOK_PUBLISH_ENABLED=false`). When enabled: **inbox upload only** until app audit grants `video.publish`; finish posting in TikTok app |
| YouTube Shorts | **Supported** with BYO Google OAuth app + Fernet `TOKEN_ENCRYPTION_KEY` + Pro/install license + clip **approved**. Desktop OAuth URI must use `http://127.0.0.1:8765/.../youtube_shorts/callback` |
| Instagram | **Not supported** — no Reels adapter in beta |
| Cloud multi-tenant | **Not supported** — stub removed; self-host / desktop only (see `docs/cloud-deploy.md` design notes) |
| Commerce | Lemon Squeezy one-time keys; license email on `order_created` fallback ✅ (`MASTER_TODO` §2.3, `tests/test_license_hardening.py`) |
| Lemon Squeezy first activate | **Network required once** when the key is not already in local DB. After activation, offline grace applies. **Cohort desktop (beta.6+):** keys are pre-seeded at boot — paste in Settings → License only. |

## Security — known limitations

| Area | Behavior |
|------|----------|
| License revoke / JWT invalidation | Revoking via `POST /api/admin/licenses/{id}/revoke` downgrades the linked user's tier to FREE, blocks re-activation, and **blocklists the `license_key_hash`** in Redis / the in-process KV set (`streamclip:revoked_license_hashes`). `verify_entitlement_token` rejects blocklisted hashes immediately (including perpetual JWTs). If the blocklist store is unreachable, verification fail-opens and logs a warning — authenticated API paths still enforce DB tier. |

## Performance expectations (informal SLIs)

From `docs/PERFORMANCE.md` with **+25% beta tolerance**:

| Scenario | GPU target | CPU target |
|----------|------------|------------|
| 1 h VOD → 5 clips | < 25 min | < ~110 min |
| API create-job (localhost) | < 500 ms | < 500 ms |

CPU-only or no NVENC paths are **slow but supported** — use `libx264` export codec.

## Docker self-host (Phase 0–1)

- **Windows:** Docker Desktop with WSL2 backend recommended; NVIDIA + NVENC for fast encode
- **macOS:** Docker Desktop for Mac supported for beta; **CPU-only** encode (no NVENC) — expect longer jobs
- Default worker queues configurable via `STREAMCLIP_WORKER_QUEUES` — use `--profile gpu` + `default`-only worker for isolation (`MASTER_TODO` §6.8, `docker-compose.prod.yml`)
- Ollama optional; virality degrades to score 0 if LLM unreachable
- Install guide: [BETA_DOWNLOAD.md](BETA_DOWNLOAD.md) (Windows & Mac tabs)

## Desktop `.exe` / `.dmg` (Phase 2)

<a id="desktop-exe-phase-2"></a>

- **Windows `.exe`:** unsigned builds trigger SmartScreen — “More info → Run anyway” until code signing (MASTER_TODO §4.10)
- **macOS `.dmg`:** not a public beta download yet; scaffold + builder notes in [MACOS_INSTALLER.md](MACOS_INSTALLER.md). Unsigned apps need **right-click → Open** until notarization (§5.3)
- First run may download **multi-GB models** (Whisper, YOLO) — allow time and disk space
- Auto-update is a **stub** — manual reinstall until §4.10 / §5
- **Scheduled publishes fire only while the app is running** — in-process mode has no external Beat service; an internal scheduler polls due posts every 60 s and catches up overdue ones on next launch (`queue.inprocess_beat`)
- **Uploads up to 5 GiB** stream to disk on desktop (`PUT /storage/...?upload=1`); need free disk under the app data dir. Docker/MinIO uses a single browser PUT (no resume) — flaky networks may need a retry
- **Distribution on desktop (beta.6+):** per-install Fernet key is generated on first boot (`install_secrets.py`). **beta.5** required manual `STREAMCLIP_DISTRIBUTION__TOKEN_ENCRYPTION_KEY`. OAuth URI: `http://127.0.0.1:8765/...`

## Reporting bugs

**In-app:** **Help menu (?)** → **Beta feedback** (questions/ideas) or **Report a bug** (breakages).
Both save to the local `bug_reports` table.

**Operator routing (recommended):** Set `OPS_WEBHOOK_URL` on api + worker —
Discord/Slack/Zapier Catch Hook/custom agent inbox. Job failures also emit
`job_failed` before testers report. See internal `docs/OPS_ALERTING.md`.

**Legacy Docker SMTP:** Optional `SMTP_HOST` + `BUG_REPORT_TO` (see `.env.example`).

```sql
SELECT id, severity, categories, message, user_id, device_id, created_at
FROM bug_reports ORDER BY created_at DESC LIMIT 50;
```

**Desktop `.exe` beta:** Bake `OPS_WEBHOOK_URL` into the operator build so
creator installs forward support forms without local SMTP. Admin list:
`GET /api/admin/bug-reports` (admin account) or SQL below.

Include: OS version, GPU model, `job_id`, relevant log snippet, steps to reproduce.

See `docs/BETA_TESTER_PLAN.md` for acceptance flows T0 / T1 / T2.
