# Build Windows installer locally and optionally upload to GitHub Releases.
param(
    [string]$Version = "1.0.0-beta.2",
    [switch]$SkipBuild,
    [switch]$PublishOnly
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$installer = Join-Path $root "apps\desktop\release\StreamClip-Setup-win-x64.exe"

if (-not $PublishOnly) {
    Write-Host "=== Building StreamClip Windows installer ===" -ForegroundColor Cyan
    & "$PSScriptRoot\build_desktop_installer.ps1"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not (Test-Path $installer)) {
    Write-Error "Installer not found: $installer"
}

$mb = [math]::Round((Get-Item $installer).Length / 1MB)
Write-Host ""
Write-Host "Installer ready ($mb MB):" -ForegroundColor Green
Write-Host "  $installer"
Write-Host ""
Write-Host "Stable download URL (after GitHub Release publish):" -ForegroundColor Cyan
Write-Host "  https://github.com/WheresWellium/StreamClip/releases/latest/download/StreamClip-Setup-win-x64.exe"
Write-Host ""
Write-Host "Docs page:" -ForegroundColor Cyan
Write-Host "  https://streamclip-henna.vercel.app/BETA_DOWNLOAD/"
Write-Host ""

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "Install GitHub CLI (gh) to publish, or upload manually:" -ForegroundColor Yellow
    Write-Host "  gh release create v$Version `"$installer`" --title `"StreamClip v$Version`""
    exit 0
}

$tag = "v$Version"
Write-Host "Publishing release $tag ..." -ForegroundColor Cyan
gh release create $tag $installer `
    --title "StreamClip $tag" `
    --notes "Windows 64-bit installer. SmartScreen may warn on unsigned beta builds - More info, Run anyway."
if ($LASTEXITCODE -ne 0) {
    Write-Host "Release failed. If tag exists, use: gh release upload $tag `"$installer`" --clobber" -ForegroundColor Yellow
    exit $LASTEXITCODE
}

Write-Host "Published. Download link is live on BETA_DOWNLOAD.md." -ForegroundColor Green
