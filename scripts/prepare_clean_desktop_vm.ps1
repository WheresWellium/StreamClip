#Requires -Version 5.1
<#
.SYNOPSIS
  Prep the next highest-value ship item after matrix green: O4d clean-VM pack.

.DESCRIPTION
  Downloads Latest Windows installer into tmp/clean-vm-pack/, refreshes the
  beta.24 evidence stub, and prints the manual CLEAN_DESKTOP_VM_VERIFY steps.
  Does NOT invent Pass/Fail for the VM checklist.

.EXAMPLE
  .\scripts\prepare_clean_desktop_vm.ps1
  .\scripts\prepare_clean_desktop_vm.ps1 -Tag v1.0.0-beta.24
#>
param(
    [string]$Tag = "v1.0.0-beta.24",
    [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $OutDir) {
    $OutDir = Join-Path $Root "tmp\clean-vm-pack"
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$asset = "qClip-Setup-win-x64.exe"
$url = "https://github.com/WheresWellium/StreamClip/releases/download/$Tag/$asset"
$dest = Join-Path $OutDir $asset

Write-Host "Downloading $url ..."
Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
$hash = (Get-FileHash -Path $dest -Algorithm SHA256).Hash
$sizeMb = [math]::Round((Get-Item $dest).Length / 1MB, 1)

$evidence = Join-Path $Root "docs\evidence\clean-desktop-vm-beta24.md"
Write-Host ""
Write-Host "=== Clean-VM pack ready ==="
Write-Host "Installer: $dest"
Write-Host "SHA256:    $hash"
Write-Host "Size:      ${sizeMb} MB"
Write-Host "Tag:       $Tag"
Write-Host "Evidence:  $evidence"
Write-Host ""
Write-Host "Copy the .exe onto a CLEAN Windows 11 VM (no %LOCALAPPDATA%\StreamClip),"
Write-Host "then follow docs\CLEAN_DESKTOP_VM_VERIFY.md and fill OPERATOR FILL in the evidence file."
Write-Host "Do not mark Pass until the VM run completes."
Write-Host ""
Write-Host "This host has existing LocalAppData StreamClip data - it is NOT a clean VM."
exit 0
