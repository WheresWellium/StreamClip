# Canonical coverage gate — see docs/MASTER_TODO.md §3.10
# Requires: docker compose up -d (api container healthy)
param(
    [switch]$SkipBuild
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "=== StreamClip coverage gate (backend + core, not desktop) ===" -ForegroundColor Cyan
Write-Host "See docs/MASTER_TODO.md section 3.10 for scope and footguns." -ForegroundColor DarkGray
Write-Host ""

if (-not $SkipBuild) {
    Write-Host "Ensuring API image is current..." -ForegroundColor Cyan
    docker compose build api
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    docker compose up -d api
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

docker compose exec -T api pytest tests/ -m "not desktop" -q `
    --cov=backend --cov=core --cov-report=term-missing:skip-covered
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Coverage gate passed (fail_under from .coveragerc)." -ForegroundColor Green
