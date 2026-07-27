# Low-memory VM build: one image at a time (avoids Docker EOF during parallel builds).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$logFile = Join-Path $root "debug-e14e3d.log"

function Write-DebugLog {
    param([string]$HypothesisId, [string]$Message, [hashtable]$Data)
    #region agent log
    $entry = @{
        sessionId    = "e14e3d"
        hypothesisId = $HypothesisId
        location     = "vm_build_lowmem.ps1"
        message      = $Message
        data         = $Data
        timestamp    = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    } | ConvertTo-Json -Compress
    Add-Content -Path $logFile -Value $entry -Encoding utf8
    #endregion
}

Write-Host "=== qClip low-memory VM build ===" -ForegroundColor Cyan
Write-Host "Building images ONE AT A TIME (COMPOSE_PARALLEL_LIMIT=1)" -ForegroundColor Yellow

$env:COMPOSE_PARALLEL_LIMIT = "1"

Write-DebugLog "E" "build_start" @{ parallelLimit = 1 }

# Pull/start infra first (no heavy build)
Write-Host "`n[1/3] Starting infrastructure (postgres, redis, minio, ollama)..." -ForegroundColor Cyan
docker compose up -d postgres redis minio minio-init ollama
if ($LASTEXITCODE -ne 0) { Write-DebugLog "D" "infra_failed" @{ exit = $LASTEXITCODE }; exit 1 }

# Build heavy Python image once via api, then reuse layers for siblings
Write-Host "`n[2/3] Building api image (torch/whisper - slow, ~15-30 min)..." -ForegroundColor Cyan
docker compose build api
$apiOk = $LASTEXITCODE -eq 0
Write-DebugLog "A" "api_build_done" @{ ok = $apiOk; exit = $LASTEXITCODE }
if (-not $apiOk) {
    Write-Host "FAIL: api build failed. Run .\scripts\vm_docker_diagnose.ps1 and check Docker Desktop memory (Settings -> Resources -> 8 GB+)." -ForegroundColor Red
    exit 1
}

Write-Host "`n[2/3] Building worker, beat, flower (reuse cached layers)..." -ForegroundColor Cyan
foreach ($svc in @("worker", "beat", "flower")) {
    Write-Host "  Building $svc..." -ForegroundColor Gray
    docker compose build $svc
    if ($LASTEXITCODE -ne 0) {
        Write-DebugLog "A" "build_failed" @{ service = $svc; exit = $LASTEXITCODE }
        exit 1
    }
}

Write-Host "`n[2/3] Building web..." -ForegroundColor Cyan
docker compose build web
if ($LASTEXITCODE -ne 0) {
    Write-DebugLog "A" "web_build_failed" @{ exit = $LASTEXITCODE }
    exit 1
}

Write-Host "`n[3/3] Starting full stack..." -ForegroundColor Cyan
docker compose up -d
$upOk = $LASTEXITCODE -eq 0
Write-DebugLog "E" "stack_up" @{ ok = $upOk; exit = $LASTEXITCODE }
if (-not $upOk) { exit 1 }

Write-Host "`nBuild complete. Run:" -ForegroundColor Green
Write-Host "  docker compose exec -T api alembic upgrade head"
Write-Host "  .\scripts\verify_stack.ps1"
Write-Host "  .\scripts\verify_coverage.ps1"
