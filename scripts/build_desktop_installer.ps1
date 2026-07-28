# Build the qClip Windows desktop installer (ADR-001 section 4.10).
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
        Write-Host "ERROR: static/ui/index.html missing - UI build failed or was skipped." -ForegroundColor Red
        exit 1
    }
    if (-not (Test-Path $uiNext)) {
        Write-Host "ERROR: static/ui/_next missing - static export incomplete." -ForegroundColor Red
        exit 1
    }
    Write-Host "Static UI OK" -ForegroundColor Green
}

Write-Host "=== qClip desktop installer build ===" -ForegroundColor Cyan

$ffmpegExe = Join-Path $root "bin\ffmpeg\ffmpeg.exe"
$ffprobeExe = Join-Path $root "bin\ffmpeg\ffprobe.exe"
if (-not ((Test-Path $ffmpegExe) -and (Test-Path $ffprobeExe))) {
    Write-Host ""
    Write-Host "=== ffmpeg binaries missing - downloading ===" -ForegroundColor Cyan
    & "$PSScriptRoot\download_ffmpeg_windows.ps1"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
if (-not ((Test-Path $ffmpegExe) -and (Test-Path $ffprobeExe))) {
    Write-Host "ERROR: bin\ffmpeg\ffmpeg.exe and ffprobe.exe required before sidecar build." -ForegroundColor Red
    exit 1
}

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

$releaseDir = Join-Path $desktopDir "release"
$setupPath = Join-Path $releaseDir "qClip-Setup-win-x64.exe"
if (-not (Test-Path -LiteralPath $setupPath)) {
    Write-Error "Required installer missing: $setupPath. electron-builder finished but did not produce qClip-Setup-win-x64.exe."
    exit 1
}

$setup = Get-Item -LiteralPath $setupPath
$setupMB = [math]::Round($setup.Length / 1MB)
if ($setupMB -lt 50) {
    Write-Error ('Installer suspiciously small ({0} MB) - bundle may be incomplete: {1}' -f $setupMB, $setupPath)
    exit 1
}
Write-Host ""
Write-Host ('Installer ready: {0} ({1} MB)' -f $setup.FullName, $setupMB) -ForegroundColor Green

# electron-updater (apps/desktop dependency) needs latest.yml next to the NSIS artifact.
$pkgPath = Join-Path $desktopDir "package.json"
$usesElectronUpdater = $false
if (Test-Path -LiteralPath $pkgPath) {
    $pkg = Get-Content -LiteralPath $pkgPath -Raw | ConvertFrom-Json
    $usesElectronUpdater = [bool](
        ($pkg.dependencies -and $pkg.dependencies.'electron-updater') -or
        ($pkg.devDependencies -and $pkg.devDependencies.'electron-updater')
    )
}
$latestYml = Join-Path $releaseDir "latest.yml"
if ($usesElectronUpdater -and -not (Test-Path -LiteralPath $latestYml)) {
    Write-Error "latest.yml missing under $releaseDir — required for electron-updater auto-update metadata after NSIS build."
    exit 1
}
if (Test-Path -LiteralPath $latestYml) {
    Write-Host ('Update metadata ready: {0}' -f $latestYml) -ForegroundColor Green
}

if (Test-SigningConfigured) {
    Write-Host "Verifying Authenticode signature on installer..." -ForegroundColor Cyan
    & "$PSScriptRoot\sign_windows_artifact.ps1" -Path $setup.FullName -VerifyOnly
    if ($LASTEXITCODE -ne 0) {
        Write-Host "NOTE: sign_windows_artifact verify failed - electron-builder may have signed during dist." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Smoke test sidecar alone: .\scripts\verify_sidecar_exe.ps1" -ForegroundColor Cyan
