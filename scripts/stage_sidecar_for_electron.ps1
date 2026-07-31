# Stage the PyInstaller sidecar bundle for electron-builder extraResources.
# Output: apps/desktop/.staging/sidecar/ (gitignored)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$src = Join-Path $root "dist\streamclip-sidecar"
$dest = Join-Path $root "apps\desktop\.staging\sidecar"

$sidecarExe = Join-Path $src "streamclip-sidecar.exe"
if (-not (Test-Path $sidecarExe)) {
    Write-Host "Missing $src\streamclip-sidecar.exe - run scripts\build_sidecar.ps1 first." -ForegroundColor Red
    exit 1
}

# Stale-artifact guard: static/ui is embedded INSIDE the PyInstaller sidecar
# bundle. If the UI was rebuilt after the sidecar, staging would ship the OLD
# UI (the classic "it worked in beta 4/5 then silently regressed"). Fail loudly
# unless explicitly overridden.
$uiIndex = Join-Path $root "static\ui\index.html"
if (Test-Path $uiIndex) {
    $uiTime = (Get-Item $uiIndex).LastWriteTimeUtc
    $exeTime = (Get-Item $sidecarExe).LastWriteTimeUtc
    if ($uiTime -gt $exeTime) {
        Write-Host "ERROR: static/ui is newer than the sidecar bundle." -ForegroundColor Red
        Write-Host ("  static/ui/index.html: {0}Z" -f $uiTime.ToString('s')) -ForegroundColor Yellow
        Write-Host ("  sidecar exe:          {0}Z" -f $exeTime.ToString('s')) -ForegroundColor Yellow
        Write-Host "  The sidecar embeds static/ui; rebuild it (do not use -SkipSidecar after a UI change)." -ForegroundColor Yellow
        if ($env:STREAMCLIP_ALLOW_STALE_UI -ne "1") {
            Write-Host "  Set STREAMCLIP_ALLOW_STALE_UI=1 to override intentionally." -ForegroundColor Yellow
            exit 1
        }
        Write-Host "  Continuing anyway (STREAMCLIP_ALLOW_STALE_UI=1)." -ForegroundColor Yellow
    }
}

Write-Host "Staging sidecar -> apps\desktop\.staging\sidecar ..." -ForegroundColor Cyan
if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
New-Item -ItemType Directory -Path $dest -Force | Out-Null
Copy-Item -Recurse (Join-Path $src "*") $dest

$sizeMB = [math]::Round((Get-ChildItem $dest -Recurse | Measure-Object Length -Sum).Sum / 1MB)
Write-Host ('Staged sidecar ({0} MB).' -f $sizeMB) -ForegroundColor Green
