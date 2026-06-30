# Stack verification — run after `docker compose up -d`
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "Checking Docker services..."
docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"

$checks = @(
    @{ Name = "API health"; Url = "http://localhost:8000/api/health" },
    @{ Name = "API meta"; Url = "http://localhost:8000/api/meta" },
    @{ Name = "Web home"; Url = "http://localhost:3000/" }
)

foreach ($c in $checks) {
    try {
        $r = Invoke-WebRequest -Uri $c.Url -UseBasicParsing -TimeoutSec 30
        Write-Host ("OK  {0} -> {1}" -f $c.Name, $r.StatusCode) -ForegroundColor Green
    }
    catch {
        Write-Host ("FAIL {0} -> {1}" -f $c.Name, $_.Exception.Message) -ForegroundColor Red
        exit 1
    }
}

Write-Host "Running unit tests in API container..."
docker compose exec -T api pytest tests/ -q --tb=no
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Stack verification passed." -ForegroundColor Green
