# Rebuild the web container and drop its anonymous .next cache volume.
# Use after pulling header/UI changes — docker compose up --build alone often
# keeps serving the old Next.js bundle from the persisted /app/.next volume.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "Refreshing web (bust .next cache + rebuild)..." -ForegroundColor Cyan

docker compose stop web
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

docker compose rm -f -v web
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

docker compose build --no-cache web
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

docker compose up -d web
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Web refreshed: http://localhost:3000" -ForegroundColor Green
Write-Host "Expected header: Jobs | Vault | Settings | New job | account icon | ? (Help menu)"
Write-Host "Hard-refresh browser: Ctrl+Shift+R"
