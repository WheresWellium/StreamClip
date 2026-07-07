# StreamClip — Production deployment

Self-hosted AI clip pipeline: Next.js → FastAPI → Celery → Redis → Postgres → MinIO.

## 1. Single VPS + Caddy + Let's Encrypt

**Recommended box:** 4 vCPU, 16 GB RAM, 200 GB SSD (~$40–50/mo). Add NVIDIA RTX 4060 if you want GPU transcoding.

1. Install Docker Engine and Docker Compose v2.
2. Clone the repo and copy `.env.example` values into `docker-compose.yml` environment blocks (or use an `.env` file).
3. Set production secrets:
   - `POSTGRES_PASSWORD`, MinIO keys, `STREAMCLIP_AUTH__SECRET_KEY`
   - **`STREAMCLIP_AUTH__SECRET_KEY`** — **required** — generate with `openssl rand -hex 32`. Using the default value (`CHANGE_ME_IN_PRODUCTION`) logs a `SECURITY_WARNING` at startup and signs both auth and entitlement JWTs with a well-known key.
   - `STREAMCLIP_RATE_LIMIT__ENABLED=true`
   - `STREAMCLIP_LOG_JSON=true`
   - **Metrics auth** (recommended): set `STREAMCLIP_OBSERVABILITY__METRICS_API_KEY` to a random token (`openssl rand -hex 16`). Without this, the `/metrics` endpoint is restricted to loopback only when `STREAMCLIP_ENVIRONMENT=production`. Include the key in your Prometheus scrape config as `Authorization: Bearer <key>` or `X-Metrics-Key: <key>`.
   - Social distribution (publish/schedule), if enabled:
     - `STREAMCLIP_DISTRIBUTION__TOKEN_ENCRYPTION_KEY` — Fernet key for OAuth secrets (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
     - `STREAMCLIP_DISTRIBUTION__WEB_ORIGIN=https://clip.example.com`
     - `STREAMCLIP_DISTRIBUTION__YOUTUBE_PUBLISH_ENABLED=true`, `STREAMCLIP_DISTRIBUTION__TIKTOK_PUBLISH_ENABLED=false`
     - Full OAuth app setup: see `docs/distribution-runbook.md`
4. **Caddy** reverse proxy (`/etc/caddy/Caddyfile`):

```caddy
clip.example.com {
    reverse_proxy /api/* localhost:8000
    reverse_proxy /docs localhost:8000
    reverse_proxy /metrics localhost:8000
    reverse_proxy localhost:3000
}
```

5. Enable TLS automatically via Caddy. For SSE, ensure `flush_interval -1` is not buffering — StreamClip sets `X-Accel-Buffering: no` on progress routes.
6. Start: `docker compose up -d --build`
7. Run migrations once: `docker compose exec api alembic upgrade head`

**Observability:** Flower on `:5555` (restrict via firewall or Caddy auth). Prometheus scrape `http://api:8000/metrics`.

## 2. Coolify deployment

Deploy each service from the same `docker-compose.yml`:

| Service  | CPU | RAM  | Notes                          |
|----------|-----|------|--------------------------------|
| postgres | 1   | 2 GB | Persistent volume              |
| redis    | 0.5 | 512M | AOF enabled in compose         |
| minio    | 1   | 2 GB | Bucket `streamclip`            |
| ollama   | 2   | 8 GB | Pull `llama3.2` on first boot  |
| api      | 2   | 4 GB | 2 uvicorn workers              |
| worker   | 4   | 12 GB| `--queues=default,gpu` on CPU  |
| web      | 1   | 1 GB | `NEXT_PUBLIC_API_URL` = public |
| flower   | 0.5 | 256M | Optional monitoring            |

Set all `STREAMCLIP_*` env vars in Coolify per service. Mount volumes: `postgres_data`, `minio_data`, `ollama_data`, `./assets`, `./workspace`.

## 3. Backups

**Nightly Postgres:**

```bash
docker compose exec -T postgres pg_dump -U streamclip streamclip \
  | gzip > /backups/streamclip-$(date +%F).sql.gz
aws s3 cp /backups/streamclip-$(date +%F).sql.gz s3://your-bucket/db/
```

**Weekly MinIO snapshot:** use `mc mirror local/streamclip /backups/minio/` and sync off-site.

**RPO:** 24 h (nightly DB). **RTO:** ~30 min (restore DB + MinIO mirror).

## 4. Zero-downtime upgrades

1. Scale API to 2 replicas behind Caddy.
2. `docker compose pull && docker compose build api worker web`
3. `docker compose run --rm api alembic upgrade head`
4. Rolling restart: `docker compose up -d --no-deps api` (one at a time), then workers.
5. Celery `task_acks_late=True` allows in-flight jobs to complete on old workers before drain.

## 5. Cost ceiling

| Item              | Monthly est. |
|-------------------|--------------|
| VPS 4c/16G        | $35–45       |
| Optional RTX 4060 | +$15–20      |
| Backups (S3)      | $2–5         |
| **Total**         | **~$50**     |

Suitable for ~5 active creators processing a few hours of VOD per week on CPU; GPU halves transcode time.

## CPU vs GPU

Default compose runs a single worker on `default,gpu` queues with `libx264` and Whisper `medium` + `int8` — this is CPU-safe and works out of the box with zero manual overrides. For NVIDIA:

```bash
docker compose -f docker-compose.prod.yml --profile gpu up -d
```

GPU worker uses `h264_nvenc` and Whisper `float16` on CUDA. When running an isolated `gpu-worker` this way, set `STREAMCLIP_WORKER_QUEUES=default` on the main `worker` service so GPU-routed tasks (`run_transcribe`, `process_clip`) only run on `gpu-worker` instead of double-consuming on both.

## 6. Webhooks

Enable job-completion notifications for external automation (Discord bot, n8n, custom splice queue):

```yaml
# config.yaml
webhooks:
  enabled: true
  url: https://your-app.com/hooks/streamclip
  secret: your-hmac-secret
```

Payload: `job.completed` with `job_id`, `status`, `clips_done`, `clips_failed`.  
Verify `X-StreamClip-Signature: sha256=<hmac>` over the raw JSON body.

Prometheus: `streamclip_webhook_deliveries_total{result="success|failure"}`.

## 7. SLO monitoring

Scrape `GET /metrics` and alert on:

- `streamclip_active_jobs` stuck high > 2h
- `streamclip_jobs_completed_total{status="error"}` rate spike
- `streamclip_clip_render_seconds` p95 > 600s on GPU deployments
- `/api/health` `status != ok` for > 5 min
