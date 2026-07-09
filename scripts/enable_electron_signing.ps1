# Toggle electron-builder Windows signing in apps/desktop/package.json.
# When CSC_* is set, enables win.signAndEditExecutable for production releases.
param(
    [ValidateSet("Enable", "Disable", "Auto")]
    [string]$Mode = "Auto"
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

$raw = Get-Content $pkgPath -Raw
$pkg = $raw | ConvertFrom-Json
if (-not $pkg.build.win) {
    $pkg.build | Add-Member -NotePropertyName win -NotePropertyValue (@{}) -Force
}
$pkg.build.win.signAndEditExecutable = $enable
$pkg | ConvertTo-Json -Depth 20 | Set-Content $pkgPath -Encoding utf8

if ($enable) {
    $env:CSC_IDENTITY_AUTO_DISCOVERY = "true"
    Write-Host "electron-builder signing ENABLED (signAndEditExecutable=true)" -ForegroundColor Green
} else {
    $env:CSC_IDENTITY_AUTO_DISCOVERY = "false"
    Write-Host "electron-builder signing disabled (unsigned local build path)" -ForegroundColor Yellow
}
