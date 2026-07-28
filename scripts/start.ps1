# StreamClip - operator shortcut to start the Phase 0 Docker stack.
# Delegates to start_local.ps1 (compose up -d --build, migrations, verify_stack).
# Usage:
#   .\scripts\start.ps1
# Re-check without rebuild (second terminal):
#   .\scripts\health.ps1

$ErrorActionPreference = "Stop"

$here = $PSScriptRoot
$root = Split-Path -Parent $here
$startLocal = Join-Path $here "start_local.ps1"

if (-not (Test-Path -LiteralPath $startLocal)) {
    Write-Host "Missing start_local.ps1 next to start.ps1: $startLocal" -ForegroundColor Red
    exit 1
}

Write-Host "StreamClip start (Phase 0 Docker)" -ForegroundColor Cyan
Write-Host "  Wrapper -> scripts\start_local.ps1"
Write-Host "  Repo    -> $root"
Write-Host ""
Write-Host "Tips:" -ForegroundColor DarkGray
Write-Host "  - First run may pull images and models (several minutes)." -ForegroundColor DarkGray
Write-Host "  - Smoke check in another terminal: .\scripts\health.ps1" -ForegroundColor DarkGray
Write-Host "  - Full gate (unit tests): .\scripts\verify_stack.ps1" -ForegroundColor DarkGray
Write-Host ""

Set-Location $root
& $startLocal @args
exit $LASTEXITCODE