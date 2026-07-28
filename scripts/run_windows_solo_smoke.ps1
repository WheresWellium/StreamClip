# Phase A — Windows solo smoke runner (no Docker).
# Run on a clean Windows 11 host after fetching/building the installer.
#
# Usage (from repo root, elevated not required):
#   .\scripts\run_windows_solo_smoke.ps1
#   .\scripts\run_windows_solo_smoke.ps1 -InstallerPath D:\kit\installers\qClip-Setup-win-x64.exe
#   .\scripts\run_windows_solo_smoke.ps1 -SkipLaunch   # checklist + log zip only
#
# Fills docs/DESKTOP_SOLO_GATE.md evidence fields via a sidecar evidence file.

param(
    [string]$InstallerPath = "",
    [switch]$SkipLaunch,
    [string]$EvidenceOut = ""
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $InstallerPath) {
    $candidates = @(
        (Join-Path $root "apps\desktop\release\qClip-Setup-win-x64.exe"),
        (Join-Path $root "dist\installers\qClip-Setup-win-x64.exe")
    )
    $kitHits = Get-ChildItem -Path (Join-Path $root "dist") -Recurse -Filter "qClip-Setup-win-x64.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($kitHits) { $candidates = @($kitHits.FullName) + $candidates }
    $InstallerPath = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

if (-not $InstallerPath -or -not (Test-Path $InstallerPath)) {
    Write-Error @"
Windows installer not found.
Run first:
  .\scripts\fetch_desktop_artifacts.ps1 -Tag v1.0.0-beta.5
  # or ./scripts/package_desktop_solo_kit.sh then point -InstallerPath at installers\
"@
}

$sha = (Get-FileHash -Algorithm SHA256 -Path $InstallerPath).Hash
$sizeMB = [math]::Round((Get-Item $InstallerPath).Length / 1MB)
Write-Host "=== qClip Windows solo smoke ===" -ForegroundColor Cyan
Write-Host "Installer: $InstallerPath"
Write-Host "Size:      $sizeMB MB"
Write-Host "SHA256:    $sha"
Write-Host ""

if (-not $SkipLaunch) {
    Write-Host "Launching installer (SmartScreen: More info → Run anyway if prompted)..." -ForegroundColor Yellow
    Start-Process -FilePath $InstallerPath -Wait
    Write-Host ""
    Write-Host "Complete HUMAN_DESKTOP_SMOKE.md Windows steps 4–7 in the UI, then press Enter." -ForegroundColor Yellow
    [void](Read-Host)
}

$logDir = Join-Path $env:LOCALAPPDATA "qClip\logs"
if (-not (Test-Path $logDir)) {
    $legacy = Join-Path $env:LOCALAPPDATA "StreamClip\logs"
    if (Test-Path $legacy) { $logDir = $legacy }
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
if (-not $EvidenceOut) {
    $EvidenceOut = Join-Path $root "tmp\desktop-solo-smoke-win-$stamp"
}
New-Item -ItemType Directory -Force -Path $EvidenceOut | Out-Null

$logZip = Join-Path $EvidenceOut "qclip-smoke-win-logs.zip"
if (Test-Path $logDir) {
    if (Test-Path $logZip) { Remove-Item $logZip -Force }
    Compress-Archive -Path (Join-Path $logDir "*") -DestinationPath $logZip -Force
    Write-Host "Logs zipped: $logZip" -ForegroundColor Green
} else {
    Write-Host "WARNING: log dir not found yet ($logDir). Launch qClip once, then re-run with -SkipLaunch." -ForegroundColor Yellow
}

$result = Read-Host "Smoke result for DESKTOP_SOLO_GATE (PASS/FAIL)"
$notes = Read-Host "Notes (optional)"
$commit = (git rev-parse --short HEAD 2>$null)
if (-not $commit) { $commit = "unknown" }

$evidence = @"
# Windows solo smoke evidence
Date: $(Get-Date -Format o)
Host: $env:COMPUTERNAME / $env:OS
Commit: $commit
Installer: $InstallerPath
SHA256: $sha
SizeMB: $sizeMB
Result: $result
Notes: $notes
LogZip: $logZip
LogDir: $logDir
"@
$evidencePath = Join-Path $EvidenceOut "EVIDENCE.txt"
Set-Content -Path $evidencePath -Value $evidence -Encoding utf8
Write-Host ""
Write-Host "Wrote $evidencePath" -ForegroundColor Green
Write-Host "Paste Result into docs/DESKTOP_SOLO_GATE.md Phase A evidence." -ForegroundColor Cyan
Write-Host "Checklist: docs/HUMAN_DESKTOP_SMOKE.md"
