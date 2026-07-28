# StreamClip - fast operator smoke check for the Phase 0 Docker stack.
# Use while / after start_local.ps1 (or start.ps1). Does NOT run pytest.
# Exit 0 = all checks passed; exit 1 = one or more failed.
# Deeper gate: .\scripts\verify_stack.ps1

param(
    [int]$TimeoutSec = 10
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$failed = 0
$checks = 0

function Write-Check {
    param(
        [string]$Name,
        [bool]$Ok,
        [string]$Detail = ""
    )
    $script:checks++
    if ($Ok) {
        $suffix = if ($Detail) { " - $Detail" } else { "" }
        Write-Host ("OK   {0}{1}" -f $Name, $suffix) -ForegroundColor Green
    }
    else {
        $script:failed++
        $suffix = if ($Detail) { " - $Detail" } else { "" }
        Write-Host ("FAIL {0}{1}" -f $Name, $suffix) -ForegroundColor Red
    }
}

function Test-LocalPort {
    param([int]$Port)
    try {
        $client = [System.Net.Sockets.TcpClient]::new()
        $iar = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(500)
        if ($ok -and $client.Connected) {
            $client.EndConnect($iar)
            $client.Close()
            return $true
        }
        $client.Close()
        return $false
    }
    catch {
        return $false
    }
}

function Test-HttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSec
    )
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
        return @{ Ok = ($r.StatusCode -ge 200 -and $r.StatusCode -lt 400); Detail = [string]$r.StatusCode }
    }
    catch {
        return @{ Ok = $false; Detail = $_.Exception.Message }
    }
}

Write-Host "StreamClip health (operator smoke)" -ForegroundColor Cyan
Write-Host "  Fast check - no unit tests. Full gate: .\scripts\verify_stack.ps1"
Write-Host ""

# Docker daemon
$dockerOk = $false
try {
    docker info *> $null
    $dockerOk = ($LASTEXITCODE -eq 0)
}
catch {
    $dockerOk = $false
}
Write-Check -Name "Docker daemon" -Ok $dockerOk -Detail $(if ($dockerOk) { "running" } else { "start Docker Desktop, then retry" })

# Compose service snapshot (non-destructive)
if ($dockerOk) {
    Write-Host ""
    Write-Host "Compose services:" -ForegroundColor Cyan
    docker compose ps --format "table {{.Service}}`t{{.Status}}`t{{.Ports}}"
    if ($LASTEXITCODE -ne 0) {
        Write-Check -Name "docker compose ps" -Ok $false -Detail "compose failed (are you in the repo root?)"
    }
    Write-Host ""
}

Write-Host "Ports:" -ForegroundColor Cyan
$portMap = @(
    @{ Name = "Web (3000)"; Port = 3000 },
    @{ Name = "API (8000)"; Port = 8000 },
    @{ Name = "Postgres (5432)"; Port = 5432 }
)
foreach ($p in $portMap) {
    $listening = Test-LocalPort -Port $p.Port
    Write-Check -Name $p.Name -Ok $listening -Detail $(if ($listening) { "LISTENING" } else { "not listening" })
}

Write-Host ""
Write-Host "HTTP:" -ForegroundColor Cyan

$httpTargets = @(
    @{ Name = "API /api/health"; Url = "http://localhost:8000/api/health" },
    @{ Name = "API /api/meta"; Url = "http://localhost:8000/api/meta" },
    @{ Name = "API /api/health/stack"; Url = "http://localhost:8000/api/health/stack" },
    @{ Name = "Web /"; Url = "http://localhost:3000/"; Retry = $true }
)
foreach ($t in $httpTargets) {
    $res = Test-HttpOk -Url $t.Url -TimeoutSec $TimeoutSec
    if (-not $res.Ok -and $t.Retry) {
        Write-Host "  Web not ready yet; retrying once in 5s..." -ForegroundColor DarkGray
        Start-Sleep -Seconds 5
        $res = Test-HttpOk -Url $t.Url -TimeoutSec $TimeoutSec
    }
    Write-Check -Name $t.Name -Ok ([bool]$res.Ok) -Detail ([string]$res.Detail)
}

# Deep stack JSON (database required; redis reported)
try {
    $stack = Invoke-RestMethod -Uri "http://localhost:8000/api/health/stack" -TimeoutSec $TimeoutSec
    $dbOk = [bool]$stack.checks.database
    $redisOk = [bool]$stack.checks.redis
    Write-Check -Name "Stack probe database" -Ok $dbOk -Detail ("database={0} redis={1}" -f $dbOk, $redisOk)
    if (-not $redisOk) {
        Write-Host "WARN redis=false (API may still serve; workers need Redis)" -ForegroundColor Yellow
    }
    try {
        $meta = Invoke-RestMethod -Uri "http://localhost:8000/api/meta" -TimeoutSec $TimeoutSec
        if ($null -ne $meta.pipeline_mode) {
            Write-Host ("INFO pipeline_mode={0}" -f $meta.pipeline_mode) -ForegroundColor DarkGray
        }
    }
    catch { }
}
catch {
    Write-Check -Name "Stack probe database" -Ok $false -Detail "health/stack unreachable or invalid JSON"
}

Write-Host ""
if ($failed -eq 0) {
    Write-Host ("Health smoke passed ({0} checks)." -f $checks) -ForegroundColor Green
    Write-Host "  Web UI  http://localhost:3000"
    Write-Host "  API     http://localhost:8000/docs"
    exit 0
}

Write-Host ("Health smoke FAILED ({0}/{1} checks)." -f $failed, $checks) -ForegroundColor Red
Write-Host "  Start/repair: .\scripts\start.ps1   (or .\scripts\start_local.ps1)"
Write-Host "  Full verify:  .\scripts\verify_stack.ps1"
exit 1