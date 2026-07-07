# Stack verification — run after `docker compose up -d` (Phase 0 beta gate).
# Excludes @pytest.mark.desktop tests (embedded sidecar/installer; not in API image).
param(
    [switch]$SkipTests,
    [switch]$RunE2E
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "=== StreamClip Docker stack verify (Phase 0) ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "Docker services:" -ForegroundColor Cyan
docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"

$checks = @(
    @{ Name = "API health"; Url = "http://localhost:8000/api/health" },
    @{ Name = "API meta"; Url = "http://localhost:8000/api/meta" },
    @{ Name = "API health/stack"; Url = "http://localhost:8000/api/health/stack" },
    @{ Name = "Web home"; Url = "http://localhost:3000/" }
)

foreach ($c in $checks) {
    try {
        $r = Invoke-WebRequest -Uri $c.Url -UseBasicParsing -TimeoutSec 30
        Write-Host ("OK  {0} -> {1}" -f $c.Name, $r.StatusCode) -ForegroundColor Green
    }
    catch {
        Write-Host ("FAIL {0} -> {1}" -f $c.Name, $_.Exception.Message) -ForegroundColor Red
        exit 1
    }
}

# Deep stack probe: database + redis must be true
try {
    $stack = Invoke-RestMethod "http://localhost:8000/api/health/stack" -TimeoutSec 15
    $dbOk = $stack.checks.database
    $redisOk = $stack.checks.redis
    if (-not $dbOk) {
        Write-Host "FAIL health/stack: database=false" -ForegroundColor Red
        exit 1
    }
    Write-Host ("OK  stack probe: database={0} redis={1}" -f $dbOk, $redisOk) -ForegroundColor Green
}
catch {
    Write-Host "FAIL health/stack JSON parse: $_" -ForegroundColor Red
    exit 1
}

if (-not $SkipTests) {
    Write-Host ""
    Write-Host "Running server-profile unit tests in API container (desktop tests excluded)..." -ForegroundColor Cyan
    docker compose exec -T api pytest tests/ -q --tb=no -m "not desktop" --no-cov
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($RunE2E) {
    Write-Host ""
    Write-Host "Running Playwright smoke (E2E_RUN=1)..." -ForegroundColor Cyan
    Push-Location (Join-Path $root "web")
    $env:E2E_RUN = "1"
    npx playwright test e2e/happy-path.spec.ts
    $e2eOk = $LASTEXITCODE -eq 0
    Remove-Item Env:\E2E_RUN -ErrorAction SilentlyContinue
    Pop-Location
    if (-not $e2eOk) { exit $LASTEXITCODE }
}

Write-Host ""
Write-Host "Stack verification passed." -ForegroundColor Green
if (-not $RunE2E) {
    Write-Host "Optional: .\scripts\verify_stack.ps1 -RunE2E" -ForegroundColor Cyan
}
