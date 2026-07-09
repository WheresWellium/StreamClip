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

function Test-DesktopStaticUi {
    $uiIndex = Join-Path $root "static\ui\index.html"
    $uiNext = Join-Path $root "static\ui\_next"
    if (-not (Test-Path $uiIndex)) {
        Write-Host "ERROR: static/ui/index.html missing — UI build failed or was skipped." -ForegroundColor Red
        exit 1
    }
    if (-not (Test-Path $uiNext)) {
        Write-Host "ERROR: static/ui/_next missing — static export incomplete." -ForegroundColor Red
        exit 1
    }
    Write-Host "Static UI OK" -ForegroundColor Green
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
Test-DesktopStaticUi

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

& "$PSScriptRoot\verify_desktop_signing_ready.ps1" -RequireSigning:($env:STREAMCLIP_REQUIRE_SIGNED_INSTALLER -eq "1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& "$PSScriptRoot\enable_electron_signing.ps1" -Mode Auto
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

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

$setup = Get-ChildItem (Join-Path $desktopDir "release") -Filter "StreamClip-Setup-win-x64.exe" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $setup) {
    $setup = Get-ChildItem (Join-Path $desktopDir "release") -Filter "StreamClip Setup *.exe" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

if ($setup) {
    $setupMB = [math]::Round($setup.Length / 1MB)
    if ($setupMB -lt 50) {
        Write-Host "ERROR: Installer suspiciously small ($setupMB MB) — bundle may be incomplete." -ForegroundColor Red
        exit 1
    }
    Write-Host ""
    Write-Host ('Installer ready: {0} ({1} MB)' -f $setup.FullName, $setupMB) -ForegroundColor Green
    if (Test-SigningConfigured) {
        Write-Host "Verifying Authenticode signature on installer..." -ForegroundColor Cyan
        & "$PSScriptRoot\sign_windows_artifact.ps1" -Path $setup.FullName -VerifyOnly
        if ($LASTEXITCODE -ne 0) {
            Write-Host "NOTE: sign_windows_artifact verify failed — electron-builder may have signed during dist." -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "electron-builder finished but no Setup exe found under apps\desktop\release\" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Smoke test sidecar alone: .\scripts\verify_sidecar_exe.ps1" -ForegroundColor Cyan
