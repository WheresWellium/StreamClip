# Download static ffmpeg + ffprobe Windows binaries for desktop sidecar bundling.
# Places ffmpeg.exe and ffprobe.exe in bin/ffmpeg/ (required by PyInstaller spec).
#
# Source: BtbN/FFmpeg-Builds (GPL static build, no external DLL dependencies).
# Run once before scripts/build_sidecar.ps1 (or scripts/build_desktop_installer.ps1).
#
# Reproducibility: pin -Ref to a dated BtbN release tag (e.g. autobuild-2025-01-01-12-00)
# and pass -Sha256 (or set STREAMCLIP_FFMPEG_SHA256) to verify the archive. Defaults
# stay on the rolling `latest` build for convenience but WARN that it is unpinned.
#
# Usage:
#   .\scripts\download_ffmpeg_windows.ps1
#   .\scripts\download_ffmpeg_windows.ps1 -Force
#   .\scripts\download_ffmpeg_windows.ps1 -Ref autobuild-2025-01-01-12-00 -Sha256 HEX
param(
    [switch]$Force,
    [string]$Ref = $(if ($env:STREAMCLIP_FFMPEG_REF) { $env:STREAMCLIP_FFMPEG_REF } else { "latest" }),
    [string]$Sha256 = $env:STREAMCLIP_FFMPEG_SHA256
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$dest = Join-Path $root "bin\ffmpeg"

$ffmpegExe  = Join-Path $dest "ffmpeg.exe"
$ffprobeExe = Join-Path $dest "ffprobe.exe"

if (-not $Force -and (Test-Path $ffmpegExe) -and (Test-Path $ffprobeExe)) {
    Write-Host "ffmpeg binaries already present in bin\ffmpeg\ (use -Force to re-download)." -ForegroundColor Green
    exit 0
}

# BtbN keeps the inner archive name stable across tags; only the release tag path changes.
$zipUrl  = "https://github.com/BtbN/FFmpeg-Builds/releases/download/$Ref/ffmpeg-master-latest-win64-gpl.zip"
$zipPath = Join-Path $env:TEMP "ffmpeg-win64.zip"
$extractDir = Join-Path $env:TEMP "ffmpeg-win64-extract"

Write-Host "Downloading ffmpeg (GPL static build for Windows x64)..." -ForegroundColor Cyan
Write-Host "  Ref: $Ref"
Write-Host "  URL: $zipUrl"
if ($Ref -eq "latest" -and -not $Sha256) {
    Write-Host "  WARNING: using rolling 'latest' with no -Sha256 - build is not reproducible." -ForegroundColor Yellow
    Write-Host "           Pin -Ref (autobuild tag) and -Sha256 (hex) for reproducible installers." -ForegroundColor Yellow
}

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$progressPreferencePrev = $ProgressPreference
$ProgressPreference = "SilentlyContinue"   # dramatically speeds up Invoke-WebRequest
try {
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
} finally {
    $ProgressPreference = $progressPreferencePrev
}

if ($Sha256) {
    $actual = (Get-FileHash -Path $zipPath -Algorithm SHA256).Hash
    if ($actual -ne $Sha256.Trim().ToUpper()) {
        Remove-Item -Force $zipPath -ErrorAction SilentlyContinue
        Write-Host "ERROR: ffmpeg archive SHA256 mismatch." -ForegroundColor Red
        Write-Host ("  expected: {0}" -f $Sha256.Trim().ToUpper()) -ForegroundColor Yellow
        Write-Host ("  actual:   {0}" -f $actual) -ForegroundColor Yellow
        exit 1
    }
    Write-Host "  SHA256 verified." -ForegroundColor Green
}

Write-Host "Extracting..."
if (Test-Path $extractDir) { Remove-Item -Recurse -Force $extractDir }
Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force

# BtbN zip layout: ffmpeg-master-latest-win64-gpl/bin/{ffmpeg,ffprobe,ffplay}.exe
$binDir = Get-ChildItem $extractDir -Directory | Select-Object -First 1
if (-not $binDir) {
    Write-Host "Unexpected zip layout — no top-level directory found." -ForegroundColor Red
    exit 1
}
$srcBin = Join-Path $binDir.FullName "bin"

if (-not (Test-Path (Join-Path $srcBin "ffmpeg.exe"))) {
    Write-Host "Unexpected zip layout — bin\ffmpeg.exe not found under $($binDir.FullName)." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest | Out-Null }

Copy-Item (Join-Path $srcBin "ffmpeg.exe")  $ffmpegExe  -Force
Copy-Item (Join-Path $srcBin "ffprobe.exe") $ffprobeExe -Force

# Clean up temp files
Remove-Item -Recurse -Force $extractDir -ErrorAction SilentlyContinue
Remove-Item -Force $zipPath -ErrorAction SilentlyContinue

$ffmpegVer = & $ffmpegExe -version 2>&1 | Select-Object -First 1
Write-Host ""
Write-Host "ffmpeg ready in bin\ffmpeg\" -ForegroundColor Green
Write-Host "  $ffmpegVer"
Write-Host "  $(& $ffprobeExe -version 2>&1 | Select-Object -First 1)"
