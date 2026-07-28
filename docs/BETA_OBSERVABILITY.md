# Beta observability runbook

**Audience:** Phase 0 operators and technical beta testers who explicitly opt in to share local diagnostics.
**Scope:** Docker self-host beta. Desktop `.exe` testers use **Settings -> Get started** and in-app bug reports unless an operator asks for logs.

qClip does not ship Prometheus or Grafana services in `docker-compose.yml` or `docker-compose.prod.yml`. The default Phase 0 path is **health checks + log tail**. Prometheus/Grafana is optional for operators who want a dashboard around the existing `/metrics` endpoint.

---

## 1. Fast path: health + log tail

Run these from the repo root while the stack is up:

```powershell
docker compose ps
curl.exe -s http://localhost:8000/api/health
curl.exe -s http://localhost:8000/api/health/stack
curl.exe -s http://localhost:8000/api/health/models
docker compose logs api worker beat --tail 120 --no-color
```

If the optional GPU profile is running, include the GPU worker:

```powershell
docker compose --profile gpu logs api worker gpu-worker beat --tail 120 --no-color
```

Useful local consoles:

- App: `http://localhost:3000`
- API health: `http://localhost:8000/api/health`
- Stack probe: `http://localhost:8000/api/health/stack`
- Model warmup: `http://localhost:8000/api/health/models`
- Flower/Celery monitor: `http://localhost:5555`
- MinIO console: `http://localhost:9001`

---

## 2. Tester opt-in log bundle

Only request logs from testers who opt in. Ask them to run one command and attach the generated text file to the in-app bug report, GitHub beta issue, or invite-email reply.

CPU/default stack:

```powershell
docker compose logs api worker beat --tail 300 --no-color > streamclip-beta-logs.txt
```

GPU profile:

```powershell
docker compose --profile gpu logs api worker gpu-worker beat --tail 300 --no-color > streamclip-beta-logs.txt
```

Add health output when startup is the failure:

```powershell
docker compose ps > streamclip-beta-health.txt
curl.exe -s http://localhost:8000/api/health >> streamclip-beta-health.txt
curl.exe -s http://localhost:8000/api/health/stack >> streamclip-beta-health.txt
```

Privacy note for the tester prompt:

> Please do not paste secrets. Before sending logs, remove API keys, license keys, email addresses if you prefer, OAuth client secrets, webhook URLs, private video URLs, and any transcript text you do not want reviewed. Logs are used only to debug the beta issue you reported.

---

## 3. Metrics scrape

Metrics are exposed by the API when `STREAMCLIP_OBSERVABILITY__ENABLE_METRICS=true`:

```powershell
curl.exe -s http://localhost:8000/metrics
```

For non-development bridge-network scraping, set a metrics key before starting the stack:

```powershell
$env:STREAMCLIP_OBSERVABILITY__METRICS_API_KEY = "<random-long-secret>"
docker compose up -d api worker beat
curl.exe -H "X-Metrics-Key: <random-long-secret>" http://localhost:8000/metrics
```

Minimal Prometheus scrape config for an operator-managed Prometheus:

```yaml
scrape_configs:
  - job_name: streamclip-api
    metrics_path: /metrics
    static_configs:
      - targets: ["host.docker.internal:8000"]
    authorization:
      type: Bearer
      credentials: "<random-long-secret>"
```

If Prometheus runs inside the same Docker network, target `api:8000` instead. Grafana is optional; import a basic Prometheus data source and chart the beta signals below.

---

## 4. Critical beta signals

Watch these first during H+0 through H+72:

| Signal | What to watch | Why it matters |
|--------|---------------|----------------|
| `streamclip_requests_total{status=~"5.."}` | Any sustained API 5xx | Broken local stack or API regression |
| `streamclip_request_duration_seconds` p95 | >5s outside upload/create paths | UI feels stuck or API is blocked |
| `streamclip_active_jobs` | Grows and never drains | Worker/queue/storage failure |
| `streamclip_celery_tasks_in_progress` | 0 while jobs are queued, or stuck high | Worker not consuming or hung tasks |
| `streamclip_pipeline_stage_seconds{stage="transcribe"}` | Large jump vs `docs/PERFORMANCE.md` budget | GPU/Whisper fallback or model issue |
| `streamclip_pipeline_stage_seconds{stage="process_clip"}` | Large jump or timeout | Render/GPU/ffmpeg bottleneck |
| `streamclip_jobs_completed_total{status!="completed"}` | Failures/cancellations | Triage cohort blockers |
| `streamclip_clips_processed_total{status!="completed"}` | Clip render failures | Bad media, captions, reframe, or export path |
| `streamclip_publish_jobs_total{status="failed"}` | Distribution failures | OAuth, platform, or worker issue |
| `streamclip_support_tickets_open` | Any red/yellow accumulation | Beta support SLA risk |

Distribution and vault metrics are only useful when those features are in the test flow: `streamclip_publish_duration_seconds`, `streamclip_vault_saves_total`, `streamclip_vault_quota_denied_total`, and `streamclip_webhook_deliveries_total`.

---

## 5. Log patterns to grep

Copy-paste these as quick triage filters:

```powershell
docker compose logs api worker beat --tail 500 --no-color | Select-String "health_db_fail|health_redis_fail|health_storage_fail|health_ollama_fail"
docker compose logs worker --tail 500 --no-color | Select-String "pipeline_start|pipeline_dispatched|celery_task_retry|clip_failed"
docker compose logs worker --tail 500 --no-color | Select-String "transcribing|model_loaded|transcript_cache_hit|confidence_rerun_failed"
docker compose logs worker --tail 500 --no-color | Select-String "cuda_unavailable_fallback|nvenc_unavailable_fallback|tracking_failed_fallback"
docker compose logs worker --tail 500 --no-color | Select-String "publish_task_failed|vault_copy_failed|webhook_delivered|ops_webhook_sent"
docker compose logs api --tail 500 --no-color | Select-String "job_created|domain_error|sse_terminated|support_ticket"
```

Escalate immediately when logs show repeated health failures, `clip_failed`, Celery retries that never end, GPU fallback on an expected NVIDIA tester, or any API 5xx cluster tied to a tester's job id.

---

## 6. Operator cadence

During the first beta wave:

1. At H+0, start a tail in a second terminal:

   ```powershell
   docker compose logs api worker beat -f --tail 80 --no-color
   ```

2. At H+2, record `docker compose ps`, `/api/health/stack`, open support tickets, and whether at least three testers passed T0-1.
3. At H+24 and H+72, review failed jobs, support tickets, and any opt-in log bundles before updating `BETA_GO_LIVE` exit evidence.
4. If Prometheus is enabled, snapshot the critical beta signals before expanding the cohort.

