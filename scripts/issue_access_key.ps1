# Issue a qClip license key via Docker API container.
# Usage:
#   .\scripts\issue_access_key.ps1
#   .\scripts\issue_access_key.ps1 -Email you@example.com
#   .\scripts\issue_access_key.ps1 -Tier pro -Email you@example.com
#   .\scripts\issue_access_key.ps1 -List -Limit 30

param(
    [string] $Email = "",
    [ValidateSet("pro", "admin")]
    [string] $Tier = "admin",
    [switch] $List,
    [int] $Limit = 20,
    [switch] $DryRun
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$local = Join-Path $RepoRoot "scripts\issue_access_key.py"
if (-not (Test-Path $local)) {
    throw "Missing $local"
}
docker compose cp $local api:/app/scripts/issue_access_key.py | Out-Null

$dockerArgs = @("scripts/issue_access_key.py")
if ($List) {
    $dockerArgs += "--list", "--limit", "$Limit"
} else {
    if ($Email) { $dockerArgs += "--email", $Email }
    $dockerArgs += "--tier", $Tier
    if ($DryRun) { $dockerArgs += "--dry-run" }
}

docker compose exec -e PYTHONPATH=/app api python @dockerArgs
