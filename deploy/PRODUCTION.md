# StreamClip — Production deployment

Self-hosted AI clip pipeline: Next.js → FastAPI → Celery → Redis → Postgres → MinIO.

## 1. Single VPS + Caddy + Let's Encrypt

**Recommended box:** 4 vCPU, 16 GB RAM, 200 GB SSD (~$40–50/mo). Add NVIDIA RTX 4060 if you want GPU transcoding.

1. Install Docker Engine and Docker Compose v2.
2. Clone the repo and copy `.env.example` values into `docker-compose.yml` environment blocks (or use an `.env` file).
3. Set production secrets:
   - `POSTGRES_PASSWORD`, MinIO keys, `STREAMCLIP_AUTH__JWT_SECRET`
   - `STREAMCLIP_RATE_LIMIT__ENABLED=true`
   - `STREAMCLIP_LOG_JSON=true`
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

Default compose runs a single worker on `default,gpu` queues with `libx264` and Whisper `medium` + `int8`. For NVIDIA:

```bash
docker compose --profile gpu up -d
```

GPU worker uses `h264_nvenc` and Whisper `float16` on CUDA.
