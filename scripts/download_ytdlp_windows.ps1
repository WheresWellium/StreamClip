# Download yt-dlp.exe into bin/yt-dlp/ for desktop packaging (PyInstaller datas).
# Mirror of scripts/download_ffmpeg_windows.ps1.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$destDir = Join-Path $root "bin\yt-dlp"
$dest = Join-Path $destDir "yt-dlp.exe"
New-Item -ItemType Directory -Force -Path $destDir | Out-Null

$url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
Write-Host "Downloading $url -> $dest"
Invoke-WebRequest -Uri $url -OutFile $dest
$mb = [math]::Round((Get-Item $dest).Length / 1MB, 1)
Write-Host "yt-dlp ready ($mb MB): $dest" -ForegroundColor Green
