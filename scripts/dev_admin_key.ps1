# Issue a ready-to-paste ADMIN license key for local testing (Windows).
#
# Usage (repo root, stack running via .\scripts\start_local.ps1):
#   .\scripts\dev_admin_key.ps1
#   .\scripts\dev_admin_key.ps1 -Email you@example.com
#
# Prints a SCPRO-XXXX-XXXX-XXXX-XXXX admin key registered in your local DB.
# Paste it in the web UI: Settings -> License -> Activate.

param(
    [string]$Email = "dev@streamclip.local"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is required and the stack must be running (.\scripts\start_local.ps1)."
}

Write-Host "==> Issuing admin license key for $Email ..." -ForegroundColor Cyan

# issue_beta_keys.py prints CSV: email,license_key,order_id,tier
$csv = docker compose exec -T -e PYTHONPATH=/app api `
    python scripts/issue_beta_keys.py --emails $Email --tier admin 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Key issuance failed. Is the stack up? Try: .\scripts\start_local.ps1"
}

$row = $csv | Select-String -Pattern "^$([regex]::Escape($Email))," | Select-Object -First 1
if (-not $row) {
    Write-Host $csv
    Write-Error "Could not parse the license key from output above."
}
$key = ($row.ToString() -split ",")[1]

Write-Host ""
Write-Host "Admin license key (tier=admin, full access):" -ForegroundColor Green
Write-Host "  $key"
Write-Host ""
Write-Host "Activate it: open http://localhost:3000 -> Settings -> License -> paste -> Activate."
