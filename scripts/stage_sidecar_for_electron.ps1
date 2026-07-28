# Stage the PyInstaller sidecar bundle for electron-builder extraResources.
# Output: apps/desktop/.staging/sidecar/ (gitignored)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$src = Join-Path $root "dist\streamclip-sidecar"
$dest = Join-Path $root "apps\desktop\.staging\sidecar"

if (-not (Test-Path (Join-Path $src "streamclip-sidecar.exe"))) {
    Write-Host "Missing $src\streamclip-sidecar.exe - run scripts\build_sidecar.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host "Staging sidecar -> apps\desktop\.staging\sidecar ..." -ForegroundColor Cyan
if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
New-Item -ItemType Directory -Path $dest -Force | Out-Null
Copy-Item -Recurse (Join-Path $src "*") $dest

# PyInstaller datas: bin/ffmpeg → bundle root bin/ffmpeg (streamclip-sidecar.spec).
$ffmpegStaged = Join-Path $dest "bin\ffmpeg\ffmpeg.exe"
$ffprobeStaged = Join-Path $dest "bin\ffmpeg\ffprobe.exe"
if (-not ((Test-Path -LiteralPath $ffmpegStaged) -and (Test-Path -LiteralPath $ffprobeStaged))) {
    Write-Error @"
Staged sidecar is missing bundled ffmpeg/ffprobe under apps\desktop\.staging\sidecar\bin\ffmpeg\.
Expected: ffmpeg.exe and ffprobe.exe (from repo bin\ffmpeg via packaging\pyinstaller\streamclip-sidecar.spec).
Run: .\scripts\download_ffmpeg_windows.ps1
Then rebuild the sidecar: .\scripts\build_sidecar.ps1
"@
    exit 1
}
Write-Host "Staged ffmpeg/ffprobe OK (bin\ffmpeg\)." -ForegroundColor Green

$sizeMB = [math]::Round((Get-ChildItem $dest -Recurse | Measure-Object Length -Sum).Sum / 1MB)
Write-Host ('Staged sidecar ({0} MB).' -f $sizeMB) -ForegroundColor Green
