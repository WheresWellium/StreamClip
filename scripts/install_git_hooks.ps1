# Point this clone at the versioned hooks under scripts/githooks.
# Run once per clone (or after cloning): .\scripts\install_git_hooks.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$hooksPath = "scripts/githooks"
$prePush = Join-Path $root "$hooksPath\pre-push"
if (-not (Test-Path $prePush)) {
    Write-Error "Missing $prePush"
}

git config core.hooksPath $hooksPath
Write-Host "Configured core.hooksPath=$hooksPath" -ForegroundColor Green
Write-Host "pre-push will run: .\scripts\verify_henna_docs.ps1"
Write-Host "Smoke: git push (dry) or .\scripts\verify_henna_docs.ps1"
