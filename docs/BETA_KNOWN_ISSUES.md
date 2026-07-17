# StreamClip — Beta Known Issues

**Audience:** Phase 0–2 beta testers · **Owner:** core team  
**Update:** when shipping a beta wave or closing a blocker

---

## Platform limits (by design for beta)

| Area | Behavior |
|------|----------|
| TikTok | **Inbox upload only** until app audit grants `video.publish` scope; finish posting in TikTok app |
| Instagram | **Not supported** — no Reels adapter in beta |
| Cloud multi-tenant | **Not supported** — stub removed; self-host / desktop only (see `docs/cloud-deploy.md` design notes) |
| Commerce | Lemon Squeezy one-time keys; license email on `order_created` fallback ✅ (`MASTER_TODO` §2.3, `tests/test_license_hardening.py`) |
| Lemon Squeezy first activate | **Network required once** — self-hosted installs call the LS License API on first activation when the key is not already in local Postgres. After activation, offline grace applies (`licensing.offline_grace_days`). Manual cohort: run `import_invite_license.py` once before UI activate. |

## Security — known limitations

| Area | Behavior |
|------|----------|
| License revoke / JWT invalidation | Revoking a license via `POST /api/admin/licenses/{id}/revoke` immediately downgrades the linked user's tier to FREE and blocks re-activation. However, any **entitlement JWT** previously issued at activation time (stored in the license file or passed as a Bearer token) remains cryptographically valid until its `exp` claim — up to 100 years for one-time-purchase perpetual tokens. Full immediate invalidation requires a server-side **jti blocklist** (not yet implemented — `MASTER_TODO §10.9`). Practical mitigation: the JWT is machine-bound (`machine_id` claim), so revoked-tier API calls still fail the DB tier check; the JWT only unlocks the desktop entitlement path. |

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
