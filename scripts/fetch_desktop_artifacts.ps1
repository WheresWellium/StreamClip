# Fetch published desktop installers into apps/desktop/release/ (collaborator auth).
# No Docker. Companion: scripts/fetch_desktop_artifacts.sh
param(
    [string]$Tag = "v1.0.0-beta.5",
    [string]$Repo = "WheresWellium/StreamClip"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI (gh) required and authenticated."
}

$out = Join-Path $root "apps/desktop/release"
New-Item -ItemType Directory -Force -Path $out | Out-Null
Write-Host "=== Fetch desktop artifacts ($Tag) from $Repo → $out ===" -ForegroundColor Cyan

function Get-ReleaseAsset([string]$Pattern) {
    if ($Tag -eq "latest") {
        & gh release download -R $Repo -p $Pattern -D $out --clobber
    } else {
        & gh release download $Tag -R $Repo -p $Pattern -D $out --clobber
    }
    return $LASTEXITCODE -eq 0
}

if (-not (Get-ReleaseAsset "qClip-Setup-win-x64.exe")) {
    Write-Error "Windows installer not on release $Tag"
}
if (-not (Get-ReleaseAsset "latest.yml")) {
    Write-Host "NOTE: latest.yml missing" -ForegroundColor Yellow
}
if (Get-ReleaseAsset "qClip-mac-arm64.dmg") {
    Write-Host "macOS DMG fetched." -ForegroundColor Green
} else {
    Write-Host "NOTE: qClip-mac-arm64.dmg not on $Tag — build with ./scripts/build_macos_solo.sh on Apple Silicon." -ForegroundColor Yellow
}

Get-ChildItem $out -Filter "qClip-*" | Format-Table Name, Length -AutoSize
Write-Host "Done." -ForegroundColor Green
