# Collect VM/Docker resource evidence for build EOF failures (debug session e14e3d).
param(
    [string]$LogFile = (Join-Path (Split-Path -Parent $PSScriptRoot) "debug-e14e3d.log")
)
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$ts = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()

function Write-DebugLog {
    param([string]$HypothesisId, [string]$Location, [string]$Message, [hashtable]$Data)
    #region agent log
    $entry = @{
        sessionId  = "e14e3d"
        hypothesisId = $HypothesisId
        location   = $Location
        message    = $Message
        data       = $Data
        timestamp  = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    } | ConvertTo-Json -Compress
    Add-Content -Path $LogFile -Value $entry -Encoding utf8
    #endregion
}

Write-Host "=== qClip VM Docker diagnose ===" -ForegroundColor Cyan
Write-Host "Logging to: $LogFile"

# Hypothesis A/B: RAM pressure
$os = Get-CimInstance Win32_OperatingSystem
$totalGb = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
$freeGb = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
Write-DebugLog "A" "vm_docker_diagnose.ps1:ram" "host_memory" @{
    totalGb = $totalGb; freeGb = $freeGb; usedPct = [math]::Round((1 - ($freeGb / $totalGb)) * 100, 1)
}
Write-Host ("RAM: {0} GB total, {1} GB free" -f $totalGb, $freeGb)

# Hypothesis C: disk full
$drive = (Get-Item $root).PSDrive.Name
$disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$drive`:'"
$diskFreeGb = [math]::Round($disk.FreeSpace / 1GB, 2)
$diskTotalGb = [math]::Round($disk.Size / 1GB, 2)
Write-DebugLog "C" "vm_docker_diagnose.ps1:disk" "repo_disk" @{
    drive = $drive; freeGb = $diskFreeGb; totalGb = $diskTotalGb
}
Write-Host ("Disk {0}: {1} GB free / {2} GB" -f $drive, $diskFreeGb, $diskTotalGb)

# Hypothesis D/E: Docker daemon health + WSL memory
$dockerOk = $false
$dockerErr = ""
try {
    $info = docker info 2>&1 | Out-String
    $dockerOk = $LASTEXITCODE -eq 0
    if (-not $dockerOk) { $dockerErr = $info.Trim() }
} catch {
    $dockerErr = $_.Exception.Message
}
Write-DebugLog "D" "vm_docker_diagnose.ps1:docker" "docker_info" @{
    ok = $dockerOk; error = $dockerErr.Substring(0, [math]::Min(500, $dockerErr.Length))
}
if ($dockerOk) {
    Write-Host "Docker: engine running" -ForegroundColor Green
} else {
    Write-Host "Docker: NOT running - $dockerErr" -ForegroundColor Red
}

$wslMem = ""
$wslCfg = "$env:USERPROFILE\.wslconfig"
if (Test-Path $wslCfg) {
    $wslMem = Get-Content $wslCfg -Raw
}
Write-DebugLog "B" "vm_docker_diagnose.ps1:wsl" "wsl_config" @{
    path = $wslCfg; exists = (Test-Path $wslCfg); content = $wslMem.Substring(0, [math]::Min(300, $wslMem.Length))
}

# Hypothesis E: parallel build count
$buildServices = @("api", "worker", "beat", "flower", "web")
Write-DebugLog "E" "vm_docker_diagnose.ps1:compose" "parallel_build_targets" @{
    services = $buildServices; count = $buildServices.Count
    recommendation = "Use COMPOSE_PARALLEL_LIMIT=1 and scripts/vm_build_lowmem.ps1"
}

Write-Host ""
Write-Host "Recommendations:" -ForegroundColor Yellow
if ($totalGb -lt 14) { Write-Host "  - VM RAM is low ($totalGb GB). Allocate 16 GB if possible." }
if ($freeGb -lt 4) { Write-Host "  - Free RAM is low ($freeGb GB). Close apps, restart Docker Desktop." }
if ($diskFreeGb -lt 30) { Write-Host "  - Disk space low ($diskFreeGb GB free). Need 40+ GB for first build." }
if (-not $dockerOk) { Write-Host "  - Start Docker Desktop and wait for Engine running." }
Write-Host "  - Run: .\scripts\vm_build_lowmem.ps1" -ForegroundColor Cyan
