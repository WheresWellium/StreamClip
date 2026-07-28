# qClip — Beta Known Issues

**Audience:** Phase 0–2 beta testers · **Owner:** core team  
**Update:** when shipping a beta wave or closing a blocker

---

## Platform limits (by design for beta)

| Area | Behavior |
|------|----------|
| TikTok | **Off by default** (`TIKTOK_PUBLISH_ENABLED=false`). When enabled: **inbox upload only** until app audit grants `video.publish`; finish posting in TikTok app |
| YouTube Shorts | **Supported** with BYO Google OAuth app + Fernet `TOKEN_ENCRYPTION_KEY` + Pro/install license + clip **approved**. Desktop OAuth URI must use `http://127.0.0.1:8765/.../youtube_shorts/callback` |
| Instagram | **Not supported** — no Reels adapter in beta |
| Cloud multi-tenant | **Not supported** — stub removed; self-host / desktop only (see `docs/cloud-deploy.md` design notes) |
| Commerce | Lemon Squeezy one-time keys; license email on `order_created` fallback ✅ (`MASTER_TODO` §2.3, `tests/test_license_hardening.py`) |
| Lemon Squeezy first activate | **Network required once** — self-hosted installs call the LS License API on first activation when the key is not already in local Postgres. After activation, offline grace applies (`licensing.offline_grace_days`). Manual cohort: run `import_invite_license.py` once before UI activate. |

## Security — known limitations

| Area | Behavior |
|------|----------|
| License revoke / JWT invalidation | Revoking a license via `POST /api/admin/licenses/{id}/revoke` immediately downgrades the linked user's tier to FREE and blocks re-activation. Desktop entitlement JWTs are now **short-lived** (renewal window ≈ `licensing.offline_grace_days`, not 100-year perpetual tokens). `GET /api/license/status` renews a valid token or **clears** a revoked/expired one from the license file. Tokens still carry `jti` + `machine_id`; a server-side jti blocklist remains optional hardening (`MASTER_TODO §10.9`). API tier checks continue to enforce FREE after revoke even before the local file is cleared. |

## Performance expectations (informal SLIs)

From `docs/PERFORMANCE.md` with **+25% beta tolerance**:

| Scenario | GPU target | CPU target |
|----------|------------|------------|
| 1 h VOD → 5 clips | < 25 min | < ~110 min |
| API create-job (localhost) | < 500 ms | < 500 ms |

CPU-only or no NVENC paths are **slow but supported** — use `libx264` export codec.

## Desktop `.exe` / `.dmg` (primary creator path)

<a id="desktop-exe-phase-2"></a>

- **Windows `.exe`:** unsigned builds trigger SmartScreen — “More info → Run anyway” until code signing (MASTER_TODO §4.10)
- **macOS `.dmg`:** product path is `qClip-mac-arm64.dmg` (no Docker). Unsigned betas need **right-click → Open** until Developer ID + notarization (§5.3). Builders: [MACOS_INSTALLER.md](MACOS_INSTALLER.md)
- First run may download **multi-GB models** (Whisper, YOLO) — allow time and disk space
- Auto-update is a **stub** — manual reinstall until §4.10 / §5
- **Scheduled publishes fire only while the app is running** — in-process mode has no external Beat service; an internal scheduler polls due posts every 60 s and catches up overdue ones on next launch (`queue.inprocess_beat`)
- **Uploads up to 5 GiB** stream to disk on desktop (`PUT /storage/...?upload=1`); need free disk under the app data dir
- **Distribution on desktop** requires `STREAMCLIP_DISTRIBUTION__TOKEN_ENCRYPTION_KEY` (Fernet). `config/desktop.yaml` sets `web_origin` to `http://127.0.0.1:8765` for OAuth redirects
- Install walkthrough: [Desktop install guide](DESKTOP_SOLO_USER_GUIDE.md)

## Docker self-host (operators only)

- **Not** the creator install path — optional compose for operators
- **Windows:** Docker Desktop with WSL2 backend; NVIDIA + NVENC for fast encode
- **macOS:** Docker Desktop for Mac; **CPU-only** encode (no NVENC) — expect longer jobs
- Default worker queues configurable via `STREAMCLIP_WORKER_QUEUES` — use `--profile gpu` + `default`-only worker for isolation (`MASTER_TODO` §6.8, `docker-compose.prod.yml`)
- Ollama optional; virality degrades to score 0 if LLM unreachable
- MinIO browser PUT has no resume — flaky networks may need a retry
- Install guide: [BETA_DOWNLOAD.md](BETA_DOWNLOAD.md) Docker tabs

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

See the [Desktop install guide](DESKTOP_SOLO_USER_GUIDE.md) for the creator acceptance checklist.
