# Verify ADR-001 §4.2 in-process queue mode against the running Docker stack.
# Switches API to inprocess, runs targeted tests, checks startup logs, restores Celery mode.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Test-DockerRunning {
    docker info *> $null
    return $LASTEXITCODE -eq 0
}

if (-not (Test-DockerRunning)) {
    Write-Host "Docker is not running - start Docker Desktop first." -ForegroundColor Red
    exit 1
}

$prevBackend = $env:STREAMCLIP_QUEUE__BACKEND
$env:STREAMCLIP_QUEUE__BACKEND = "inprocess"

Write-Host "Switching API to in-process queue (worker/beat left running but unused)..." -ForegroundColor Cyan
docker compose up -d --force-recreate --no-deps api | Out-Null
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Waiting for API health..."
$healthy = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -eq 200) {
            $healthy = $true
            break
        }
    }
    catch {
        Start-Sleep -Seconds 2
    }
}
if (-not $healthy) {
    Write-Host "API did not become healthy within 60s." -ForegroundColor Red
    docker compose logs api --tail 40
    exit 1
}
Write-Host "OK  API health -> 200" -ForegroundColor Green

Write-Host "Checking API logs for in-process worker startup..."
Start-Sleep -Seconds 3
$logs = docker compose logs api --tail 80 2>&1 | Out-String
if ($logs -notmatch "inprocess_worker_ready") {
    Write-Host "FAIL in-process worker did not log inprocess_worker_ready" -ForegroundColor Red
    Write-Host $logs
    exit 1
}
Write-Host "OK  inprocess_worker_ready in API logs" -ForegroundColor Green

Write-Host "Running in-process unit tests in API container..."
docker compose exec -T api pytest tests/test_inprocess_worker.py tests/test_task_dispatch.py -q --no-cov --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Verifying settings load in-process inside container..."
docker compose exec -T api env PYTHONPATH=/app python scripts/check_inprocess_config.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Restoring default Celery queue backend on API..."
if ($null -eq $prevBackend) {
    Remove-Item Env:STREAMCLIP_QUEUE__BACKEND -ErrorAction SilentlyContinue
}
else {
    $env:STREAMCLIP_QUEUE__BACKEND = $prevBackend
}
docker compose up -d --force-recreate --no-deps api | Out-Null
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "In-process verification passed." -ForegroundColor Green
