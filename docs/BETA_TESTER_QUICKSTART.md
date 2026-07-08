# StreamClip — Beta Quickstart (15 minutes)

!!! note "Creators installing the Windows app"
    **No Docker required.** Use the [**Windows installer download**](BETA_DOWNLOAD.md) instead of this guide.

For **Phase 0 technical beta (Docker self-host)**: Docker on Windows 10/11. Full acceptance flows live in `docs/BETA_TESTER_PLAN.md` §4.3.

---

## Prerequisites

- Docker Desktop (WSL2 backend on Windows)
- 16 GB RAM minimum; **NVIDIA GPU** strongly recommended (NVENC path)
- Ports free: `3000` (web), `8000` (API), `9000` (MinIO console optional)

---

## 1. Get the code

```powershell
git clone <PRIVATE_REPO_URL> streamclip
cd streamclip
```

Or extract the beta zip to a folder and `cd` into it.

---

## 2. Configure environment

```powershell
Copy-Item .env.example .env
# Defaults work for local beta (MinIO + Ollama in Docker).
# Optional: set STREAMCLIP_DISTRIBUTION__YOUTUBE_PUBLISH_ENABLED=true after OAuth setup.
```

---

## 3. Start the stack

```powershell
docker compose up -d
```

Wait until Postgres, Redis, MinIO, Ollama, API, workers, and web are healthy (~2–5 min first pull).

---

## 4. Verify before your first job

```powershell
.\scripts\verify_stack.ps1
```

**Must exit 0.** If it fails, do not create jobs — post logs in the beta channel.

Manual checks:

- UI: http://localhost:3000 — “Jet Stream” home loads
- API: http://localhost:8000/api/health — `status` is `ok` or `degraded`, `database` is true
- Stack: http://localhost:8000/api/health/stack — `checks.database` and `checks.redis` true; `checks.cuda` / `checks.nvenc` show GPU availability

**Production compose** (GHCR images, no bind mounts): see `.env.production.example` and
`docker compose -f docker-compose.prod.yml --env-file .env.production up -d`.
Use `--profile gpu` with `STREAMCLIP_WORKER_QUEUES=default` for NVIDIA queue isolation.

---

## 5. Create your first job

1. Open http://localhost:3000
2. Click **New job**
3. Paste a **public** VOD or clip URL (Twitch, YouTube, Kick, or direct `.mp4`)
4. Submit — job id appears under Recent jobs
5. Watch progress until status **done** and at least one clip preview shows

**Beta tolerance:** GPU 1h VOD → 5 clips target **< 25 min**; CPU **< 90 min** (see `docs/PERFORMANCE.md`).

---

## 6. Approve and publish (YouTube)

1. Open a finished clip → adjust title/boundaries if needed → **Approve**
2. Settings → Distribution → connect **YouTube Shorts** (OAuth)
3. Queue publish from the clip or batch publish UI
4. Pass: publish status **published** or a **clear** error message (not silent hang)

**Known:** TikTok direct publish may be inbox-only until app audit — see known-issues list.

---

## 7. Optional — Vault & license

- **Vault:** Save an approved clip; confirm quota message if you hit free-tier limit
- **Pro key:** Settings → License → paste `SCPRO-…` from your beta email; confirm Pro gates unlock

---

## 8. When something breaks

Use **Report a bug** in the app header (saved to local DB; email only if operator
configured `SMTP_HOST` + `BUG_REPORT_TO` — see `.env.example`).

Include in your report:

1. Job id (or publish job id)
2. GPU model + `docker compose exec api nvidia-smi` output if GPU worker
3. Last 50 lines: `docker compose logs api worker --tail 50`
4. Result of `verify_stack.ps1`

Post to the channel linked in your invite email (Discord / GitHub Discussions).
Operators can list saved reports via `GET /api/admin/bug-reports` (admin account).

---

## 9. Stop the stack

```powershell
docker compose down
```

Data persists in Docker volumes (`postgres_data`, etc.) unless you add `-v` (wipes DB).

---

*Phase 0 only. Phase 1/2 delivery (GHCR, desktop `.exe`) is documented in `docs/BETA_TESTER_PLAN.md`.*
