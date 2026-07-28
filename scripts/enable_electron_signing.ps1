# Toggle electron-builder Windows signing in apps/desktop/package.json.
# Canonical runbook: docs/DESKTOP_SIGNING.md
# When CSC_* is set, enables win.signAndEditExecutable for production releases.
# Uses Node to patch JSON so PowerShell ConvertTo-Json cannot corrupt "&&" in scripts.
#
#   .\scripts\enable_electron_signing.ps1 -Mode Auto
#   .\scripts\enable_electron_signing.ps1 -Mode Auto -DryRun   # no package.json write
param(
    [ValidateSet("Enable", "Disable", "Auto")]
    [string]$Mode = "Auto",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$pkgPath = Join-Path $root "apps\desktop\package.json"

if (-not (Test-Path $pkgPath)) {
    Write-Error "Missing $pkgPath"
}

$signingConfigured = [bool]$env:CSC_LINK -and [bool]$env:CSC_KEY_PASSWORD
$enable = switch ($Mode) {
    "Enable" { $true }
    "Disable" { $false }
    "Auto" { $signingConfigured }
}

$current = node --input-type=commonjs -e "const p=require(process.argv[1]); process.stdout.write(String(!!(p.build&&p.build.win&&p.build.win.signAndEditExecutable)));" -- $pkgPath
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($DryRun) {
    Write-Host "=== enable_electron_signing dry-run ===" -ForegroundColor Cyan
    Write-Host ("Mode:                      {0}" -f $Mode)
    Write-Host ("CSC_* configured:          {0}" -f $signingConfigured)
    Write-Host ("Current signAndEditExecutable: {0}" -f $current)
    Write-Host ("Would set signAndEditExecutable: {0}" -f $(if ($enable) { "true" } else { "false" }))
    Write-Host ("Would set CSC_IDENTITY_AUTO_DISCOVERY: {0}" -f $(if ($enable) { "true" } else { "false" }))
    Write-Host "Dry-run complete (package.json not modified)." -ForegroundColor Green
    exit 0
}

$enableJson = if ($enable) { "true" } else { "false" }
& node --input-type=commonjs -e @"
const fs = require('fs');
const path = process.argv[1];
const enable = process.argv[2] === 'true';
const pkg = JSON.parse(fs.readFileSync(path, 'utf8'));
pkg.build = pkg.build || {};
pkg.build.win = pkg.build.win || {};
pkg.build.win.signAndEditExecutable = enable;
fs.writeFileSync(path, JSON.stringify(pkg, null, 2) + '\n', 'utf8');
"@ -- $pkgPath $enableJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($enable) {
    $env:CSC_IDENTITY_AUTO_DISCOVERY = "true"
    Write-Host "electron-builder signing ENABLED (signAndEditExecutable=true)" -ForegroundColor Green
} else {
    $env:CSC_IDENTITY_AUTO_DISCOVERY = "false"
    Write-Host "electron-builder signing disabled (unsigned local build path)" -ForegroundColor Yellow
}
