# Branch coverage gate — hot-path modules (MASTER_TODO §3.10)
# Phase 1+ target: ≥85% branch on listed modules.
# Phase 0: measure only; does not fail the 95% line gate.
param(
    [switch]$SkipBuild,
    [int]$FailUnderBranch = 0
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "=== qClip hot-path branch coverage (§3.7) ===" -ForegroundColor Cyan
Write-Host "Modules: pipeline_tasks, sse, job_service, core/distribution" -ForegroundColor DarkGray
Write-Host ""

if (-not $SkipBuild) {
    docker compose build api | Out-Null
    docker compose up -d api | Out-Null
}

$modules = @(
    "core.tasks.pipeline_tasks",
    "backend.services.sse",
    "backend.services.job_service",
    "core.distribution"
)

$covArgs = @("--cov-branch")
foreach ($m in $modules) {
    $covArgs += "--cov=$m"
}

$covOutput = & docker compose exec -T api pytest tests/ -m "not desktop" -q -o addopts= --cov-branch @covArgs `
    --cov-report=term-missing:skip-covered --cov-fail-under=0 2>&1
$covText = ($covOutput | Out-String)
$covOutput | ForEach-Object { Write-Host $_ }

if ($LASTEXITCODE -ne 0) {
    Write-Host "Branch measurement run failed (tests)." -ForegroundColor Red
    exit $LASTEXITCODE
}

if ($FailUnderBranch -gt 0 -and $covText -match 'Branch cover: (\d+)%') {
    $pct = [int]$Matches[1]
    if ($pct -lt $FailUnderBranch) {
        Write-Host "Branch coverage $pct% below fail-under $FailUnderBranch%." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Branch measurement complete (Phase 0: informational; set -FailUnderBranch 85 for Phase 1 gate)." -ForegroundColor Green
