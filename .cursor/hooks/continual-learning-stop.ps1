# Continual learning: periodically mine agent-transcripts into AGENTS.md via the
# agents-memory-updater subagent. PowerShell port of the continual-learning plugin's
# stop hook (bun unavailable in this environment); same cadence/state semantics.
$ErrorActionPreference = 'Stop'
$raw = [Console]::In.ReadToEnd()
$hookInput = $raw | ConvertFrom-Json

$stateDir = '.cursor/hooks/state'
$statePath = Join-Path $stateDir 'continual-learning.json'
$indexPath = Join-Path $stateDir 'continual-learning-index.json'
if (-not (Test-Path $stateDir)) {
    New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
}

$state = @{
    version               = 1
    lastRunAtMs           = 0
    turnsSinceLastRun     = 0
    lastTranscriptMtimeMs = 0
    lastProcessedGenId    = ''
    trialStartedAtMs      = 0
}
if (Test-Path $statePath) {
    try {
        $loaded = Get-Content $statePath -Raw | ConvertFrom-Json
        if ($loaded.version -eq 1) {
            $state.lastRunAtMs = [long]$loaded.lastRunAtMs
            $state.turnsSinceLastRun = [int]$loaded.turnsSinceLastRun
            $state.lastTranscriptMtimeMs = [long]$loaded.lastTranscriptMtimeMs
            $state.lastProcessedGenId = [string]$loaded.lastProcessedGenId
            $state.trialStartedAtMs = [long]$loaded.trialStartedAtMs
        }
    } catch { }
}

# De-dupe: hooks may re-fire for the same generation.
if ($hookInput.generation_id -and $hookInput.generation_id -eq $state.lastProcessedGenId) {
    Write-Output '{}'
    exit 0
}
$state.lastProcessedGenId = [string]$hookInput.generation_id

$countedTurn = ($hookInput.status -eq 'completed' -and $hookInput.loop_count -eq 0)
if ($countedTurn) {
    $state.turnsSinceLastRun++
}
$nowMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()

# Trial mode: faster cadence for the first 24h so the loop is easy to observe, then
# fall back to the conservative default cadence.
$trialDurationMinutes = 24 * 60
$trialMinTurns = 3
$trialMinMinutes = 15
$defaultMinTurns = 10
$defaultMinMinutes = 120

if ($countedTurn -and $state.trialStartedAtMs -eq 0) {
    $state.trialStartedAtMs = $nowMs
}
$inTrialWindow = ($state.trialStartedAtMs -gt 0) -and (($nowMs - $state.trialStartedAtMs) -lt ($trialDurationMinutes * 60000))

$minTurns = if ($inTrialWindow) { $trialMinTurns } else { $defaultMinTurns }
$minMinutes = if ($inTrialWindow) { $trialMinMinutes } else { $defaultMinMinutes }

$minutesSinceLastRun = if ($state.lastRunAtMs -gt 0) {
    [math]::Floor(($nowMs - $state.lastRunAtMs) / 60000)
} else { [int]::MaxValue }

$transcriptMtimeMs = 0
if ($hookInput.transcript_path -and (Test-Path $hookInput.transcript_path)) {
    $transcriptMtimeMs = [DateTimeOffset]::new((Get-Item $hookInput.transcript_path).LastWriteTimeUtc).ToUnixTimeMilliseconds()
}
$hasTranscriptAdvanced = ($transcriptMtimeMs -gt 0) -and ($transcriptMtimeMs -gt $state.lastTranscriptMtimeMs)

$shouldTrigger = $countedTurn -and ($state.turnsSinceLastRun -ge $minTurns) -and ($minutesSinceLastRun -ge $minMinutes) -and $hasTranscriptAdvanced

if ($shouldTrigger) {
    $state.lastRunAtMs = $nowMs
    $state.turnsSinceLastRun = 0
    $state.lastTranscriptMtimeMs = $transcriptMtimeMs
    $state | ConvertTo-Json | Set-Content $statePath -Encoding utf8

    $message = @"
Run the continual-learning flow now. Call the ``agents-memory-updater`` subagent for the
full memory update: use incremental transcript processing with index file ``$indexPath``
(only consider transcripts not in the index or with mtime newer than indexed mtime).
Have it refresh index mtimes, remove entries for deleted transcripts, and update
AGENTS.md only for high-signal recurring user corrections and durable workspace facts.
Exclude one-off/transient details and secrets. If no meaningful updates exist, respond
exactly: No high-signal memory updates.
"@
    Write-Output (@{ followup_message = $message } | ConvertTo-Json -Compress)
    exit 0
}

$state | ConvertTo-Json | Set-Content $statePath -Encoding utf8
Write-Output '{}'
