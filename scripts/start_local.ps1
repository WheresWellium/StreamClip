# Local dev / Phase 0 beta — run the full stack with Docker (not the .exe).
# The desktop .exe (ADR-001) replaces Docker later; until then this is the test path.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Test-DockerRunning {
    docker info *> $null
    return $LASTEXITCODE -eq 0
}

Write-Host "qClip — local stack" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-DockerRunning)) {
    Write-Host "Docker Desktop is not running." -ForegroundColor Red
    Write-Host "  1. Start Docker Desktop and wait until it shows 'Running'"
    Write-Host "  2. Re-run: .\scripts\start_local.ps1"
    Write-Host ""
    Write-Host "Docker self-host: docs/GET_STARTED.md (Operators section)"
    Write-Host "Creators (desktop .exe): docs/GET_STARTED.md"
    exit 1
}

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example"
    }
}

Write-Host "Starting services (first run may pull images + models)..."
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Running migrations..."
docker compose exec -T api alembic upgrade head
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Verifying stack..."
& "$PSScriptRoot\verify_stack.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Ready:" -ForegroundColor Green
Write-Host "  Web UI   http://localhost:3000"
Write-Host "  API docs http://localhost:8000/docs"
Write-Host "  Flower   docker compose --profile dev up -d flower  (optional)"
Write-Host ""
Write-Host "Create a job from the web UI or POST /api/jobs. GPU: docker compose --profile gpu up -d gpu-worker"
