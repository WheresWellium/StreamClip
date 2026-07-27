# Canonical coverage gate — see docs/MASTER_TODO.md §3.10
# Requires: docker compose up -d (api container healthy)
param(
    [switch]$SkipBuild
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "=== qClip coverage gate (backend + core, not desktop) ===" -ForegroundColor Cyan
Write-Host "See docs/MASTER_TODO.md section 3.10 for scope and footguns." -ForegroundColor DarkGray
Write-Host ""

if (-not $SkipBuild) {
    Write-Host "Ensuring API image is current..." -ForegroundColor Cyan
    docker compose build api
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    docker compose up -d api
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$covOutput = & docker compose exec -T api pytest tests/ -m "not desktop" -q `
    --cov=backend --cov=core --cov-report=term-missing:skip-covered 2>&1
$covText = ($covOutput | Out-String)
$covOutput | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($covText -match 'FAIL Required test coverage of 95') { exit 1 }
if ($covText -match '\d+ failed') { exit 1 }

Write-Host ""
Write-Host "Coverage gate passed (fail_under from .coveragerc)." -ForegroundColor Green
