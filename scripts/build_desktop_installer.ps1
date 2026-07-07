# Build the StreamClip Windows desktop installer (ADR-001 §4.10).
#
# Pipeline: static UI -> PyInstaller sidecar -> stage -> electron-builder (NSIS).
# Code signing (optional): set CSC_LINK (path to .pfx) and CSC_KEY_PASSWORD.
#
# Usage:
#   .\scripts\build_desktop_installer.ps1
#   .\scripts\build_desktop_installer.ps1 -SkipUi -SkipSidecar   # reuse existing artifacts
#   $env:STREAMCLIP_SKIP_PYINSTALLER='1'; .\scripts\build_desktop_installer.ps1  # skip sidecar rebuild
param(
    [switch]$SkipUi,
    [switch]$SkipSidecar,
    [switch]$SkipElectronBuild
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$desktopDir = Join-Path $root "apps\desktop"

function Test-SigningConfigured {
    return [bool]$env:CSC_LINK -and [bool]$env:CSC_KEY_PASSWORD
}

Write-Host "=== StreamClip desktop installer build ===" -ForegroundColor Cyan

if (-not $SkipUi) {
    Write-Host ""
    Write-Host "=== Static UI ===" -ForegroundColor Cyan
    & "$PSScriptRoot\build_desktop_ui.ps1"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "Skipping static UI build (-SkipUi)." -ForegroundColor Yellow
}

if (-not $SkipSidecar) {
    Write-Host ""
    Write-Host "=== PyInstaller sidecar ===" -ForegroundColor Cyan
    & "$PSScriptRoot\build_sidecar.ps1"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "Skipping sidecar build (-SkipSidecar)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Stage sidecar for Electron ===" -ForegroundColor Cyan
& "$PSScriptRoot\stage_sidecar_for_electron.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Test-SigningConfigured)) {
    Write-Host ""
    Write-Host "NOTE: CSC_LINK / CSC_KEY_PASSWORD not set — installer will be UNSIGNED." -ForegroundColor Yellow
    Write-Host "      SmartScreen will warn on first run. See packaging/installer/README.md." -ForegroundColor Yellow
    $env:CSC_IDENTITY_AUTO_DISCOVERY = "false"
}

if ($SkipElectronBuild) {
    Write-Host "Skipping electron-builder (-SkipElectronBuild)." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "=== Electron compile + NSIS installer ===" -ForegroundColor Cyan
Push-Location $desktopDir
if (-not (Test-Path "node_modules")) {
    npm ci
    if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
}
npm run build
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
npm run dist
$distOk = $LASTEXITCODE -eq 0
Pop-Location
if (-not $distOk) { exit $LASTEXITCODE }

$setup = Get-ChildItem (Join-Path $desktopDir "release") -Filter "StreamClip Setup *.exe" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($setup) {
    $setupMB = [math]::Round($setup.Length / 1MB)
    Write-Host ""
    Write-Host ('Installer ready: {0} ({1} MB)' -f $setup.FullName, $setupMB) -ForegroundColor Green
    if (Test-SigningConfigured) {
        Write-Host "Signed with certificate from CSC_LINK." -ForegroundColor Green
    }
} else {
    Write-Host "electron-builder finished but no Setup exe found under apps\desktop\release\" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Smoke test sidecar alone: .\scripts\verify_sidecar_exe.ps1" -ForegroundColor Cyan
