# Emits a follow-up before Cursor compacts context so durable state is flushed to disk.
$ErrorActionPreference = 'Stop'
$null = [Console]::In.ReadToEnd()

$message = @'
Context compaction is imminent. Before continuing:
1. Update docs/SESSION_STATE.md (goal, blockers, decisions, next steps, key paths) in <=60 lines.
2. Update AGENTS.md only if durable preferences or workspace facts changed.
Do not paste tool output into chat. Proceed with the user's task using SESSION_STATE as source of truth.
'@

Write-Output (@{ followup_message = $message } | ConvertTo-Json -Compress)
