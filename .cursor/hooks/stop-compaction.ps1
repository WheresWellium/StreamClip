# Periodically nudge SESSION_STATE refresh so summarized threads stay executable.
$ErrorActionPreference = 'Stop'
$raw = [Console]::In.ReadToEnd()
$input = $raw | ConvertFrom-Json

if ($input.status -ne 'completed' -or $input.loop_count -ne 0) {
    Write-Output '{}'
    exit 0
}

$stateDir = '.cursor/hooks/state'
$statePath = Join-Path $stateDir 'compaction.json'
if (-not (Test-Path $stateDir)) {
    New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
}

$state = @{
    version           = 1
    turnsSinceRefresh = 0
    lastRunAtMs       = 0
}
if (Test-Path $statePath) {
    try {
        $loaded = Get-Content $statePath -Raw | ConvertFrom-Json
        if ($loaded.version -eq 1) {
            $state.turnsSinceRefresh = [int]$loaded.turnsSinceRefresh
            $state.lastRunAtMs = [long]$loaded.lastRunAtMs
        }
    } catch { }
}

$minTurns = 6
$minMinutes = 45
$state.turnsSinceRefresh++
$nowMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
$minutesSince = if ($state.lastRunAtMs -gt 0) {
    [math]::Floor(($nowMs - $state.lastRunAtMs) / 60000)
} else { [int]::MaxValue }

if ($state.turnsSinceRefresh -ge $minTurns -and $minutesSince -ge $minMinutes) {
    $state.turnsSinceRefresh = 0
    $state.lastRunAtMs = $nowMs
    $state | ConvertTo-Json | Set-Content $statePath -Encoding utf8

    $message = @'
Refresh docs/SESSION_STATE.md from this thread (<=60 lines): current goal, blockers, decisions, ordered next steps, key paths. Update AGENTS.md only for durable preference/fact changes. Then continue the task without repeating prior tool output.
'@
    Write-Output (@{ followup_message = $message } | ConvertTo-Json -Compress)
    exit 0
}

$state | ConvertTo-Json | Set-Content $statePath -Encoding utf8
Write-Output '{}'
