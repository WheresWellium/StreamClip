# Phase 0 cohort exit - automated evidence snapshot (GAP O4 / MASTER 8.16).
# Captures everything checkable from the operator machine into a timestamped
# markdown file under docs/evidence/, plus an OPERATOR FILL block for the
# window-specific human facts (tester counts, triage, go/no-go).
#
# Fail-soft: anything not reachable (Docker down, API down, gh missing)
# produces a SKIP line in the evidence file - the script never crashes.
# Non-interactive; PowerShell 5.1 compatible; no secrets captured.
#
# Usage (repo root):
#   .\scripts\capture_phase0_evidence.ps1 -Help
#   .\scripts\capture_phase0_evidence.ps1 -Label T0
#   .\scripts\capture_phase0_evidence.ps1 -Label H72 -Note "wave 1 close-out"
#
# Exit codes:
#   0  evidence file written (even if some sections are SKIP)
#   1  could not write the evidence file (bad OutDir / disk)
param(
    [switch]$Help,
    [ValidateSet("T0", "H2", "H24", "H48", "H72")]
    [string]$Label = "T0",
    [string]$Note = "",
    [string]$OutDir = "",
    [int]$TimeoutSec = 10
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Show-Help {
    @"
capture_phase0_evidence.ps1 - Phase 0 exit evidence snapshot (GAP O4)

  -Help        Show this help and exit 0
  -Label       Evidence window: T0 | H2 | H24 | H48 | H72   (default T0)
  -Note        Free-text note recorded in the file header
  -OutDir      Output folder (default docs\evidence)
  -TimeoutSec  HTTP probe timeout (default 10)

What it captures automatically (fail-soft; unreachable => SKIP line):
  git SHA/branch/dirty count - docker compose ps - port probes (3000/8000/5432)
  /api/health - /api/meta - /api/health/stack JSON - job counts by status
  bug_reports count (last 72h) - GitHub open beta bugs (gh, if installed)
  desktop release row from docs/BETA_DOWNLOAD.md - coverage note from SESSION_STATE

What it can NOT capture (appended as an OPERATOR FILL block per window):
  tester T0-1..T0-4 outcomes, P0/P1 triage decisions, go/no-go call.

Workflow (docs/BETA_COHORT_EXIT.md):
  T0/H+0 : .\scripts\capture_phase0_evidence.ps1 -Label T0
  H+2    : .\scripts\capture_phase0_evidence.ps1 -Label H2
  H+24   : .\scripts\capture_phase0_evidence.ps1 -Label H24
  H+48   : .\scripts\capture_phase0_evidence.ps1 -Label H48
  H+72   : .\scripts\capture_phase0_evidence.ps1 -Label H72
Then fill the OPERATOR FILL block in the generated file and paste its path
into the matching Evidence cell of docs/BETA_COHORT_EXIT.md.
"@ | Write-Host
}

if ($Help) {
    Show-Help
    exit 0
}

if (-not $OutDir) { $OutDir = Join-Path $root "docs\evidence" }

$lines = New-Object System.Collections.Generic.List[string]
function Add-Line([string]$Text = "") { $script:lines.Add($Text) | Out-Null }

function Invoke-Capture {
    # Runs a scriptblock; on any error emits a SKIP line instead of failing.
    param(
        [string]$Name,
        [scriptblock]$Block
    )
    try {
        & $Block
    }
    catch {
        Add-Line ("- SKIP {0} - {1}" -f $Name, $_.Exception.Message.Split("`n")[0])
    }
}

function Test-LocalPort([int]$Port) {
    try {
        $client = [System.Net.Sockets.TcpClient]::new()
        $iar = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(500)
        if ($ok -and $client.Connected) {
            $client.EndConnect($iar); $client.Close(); return $true
        }
        $client.Close(); return $false
    }
    catch { return $false }
}

$nowUtc = [DateTime]::UtcNow
$stamp = $nowUtc.ToString("yyyyMMdd-HHmmss")
$iso = $nowUtc.ToString("yyyy-MM-ddTHH:mm:ssZ")
$fileName = "phase0-{0}-{1}.md" -f $Label.ToLower(), $stamp

Write-Host ("Phase 0 evidence snapshot - label {0}" -f $Label) -ForegroundColor Cyan

# --- Header -----------------------------------------------------------------
Add-Line ("# Phase 0 evidence - {0}" -f $Label)
Add-Line ""
Add-Line "| Field | Value |"
Add-Line "|-------|-------|"
Add-Line ("| Window | {0} |" -f $Label)
Add-Line ("| Captured (UTC) | {0} |" -f $iso)
Add-Line ("| Machine | {0} |" -f $env:COMPUTERNAME)
if ($Note) { Add-Line ("| Note | {0} |" -f $Note) }
Add-Line "| Tool | ``scripts/capture_phase0_evidence.ps1`` |"

# --- Git --------------------------------------------------------------------
Invoke-Capture -Name "git" -Block {
    $sha = (git rev-parse --short HEAD 2>$null)
    if ($LASTEXITCODE -ne 0) { throw "git rev-parse failed" }
    $branch = (git rev-parse --abbrev-ref HEAD 2>$null)
    $dirty = @(git status --porcelain 2>$null).Count
    Add-Line ("| Git | ``{0}`` on ``{1}`` ({2} uncommitted paths) |" -f $sha, $branch, $dirty)
}

# --- Coverage note (from SESSION_STATE, no Docker run) ------------------------
Invoke-Capture -Name "coverage note" -Block {
    $ss = Join-Path $root "docs\SESSION_STATE.md"
    $covLine = ""
    if (Test-Path $ss) {
        $covLine = (Get-Content $ss | Where-Object { $_ -match "Coverage gate" } | Select-Object -First 1)
    }
    if ($covLine) {
        Add-Line ("| Coverage (SESSION_STATE) | {0} |" -f $covLine.Trim().TrimStart("- ").Replace("|", "/"))
    }
    else {
        Add-Line "| Coverage (SESSION_STATE) | SKIP - no 'Coverage gate' line found |"
    }
}

# --- Desktop release row ------------------------------------------------------
Invoke-Capture -Name "desktop release" -Block {
    $dl = Join-Path $root "docs\BETA_DOWNLOAD.md"
    $verLine = (Get-Content $dl | Where-Object { $_ -match "1\.0\.0-beta\.\d+" } | Select-Object -First 1)
    if ($verLine -match "(1\.0\.0-beta\.\d+)") {
        Add-Line ("| Desktop release (BETA_DOWNLOAD) | {0} |" -f $Matches[1])
    }
    else { throw "no beta version found in BETA_DOWNLOAD.md" }
}
Add-Line ""

# --- Docker / compose ---------------------------------------------------------
Add-Line "## Stack snapshot"
Add-Line ""
$dockerOk = $false
Invoke-Capture -Name "docker daemon" -Block {
    docker info *> $null
    $script:dockerOk = ($LASTEXITCODE -eq 0)
    if ($script:dockerOk) { Add-Line "- OK Docker daemon running" }
    else { Add-Line "- SKIP Docker daemon not running" }
}

if ($dockerOk) {
    Invoke-Capture -Name "docker compose ps" -Block {
        $ps = docker compose ps --format "table {{.Service}}`t{{.Status}}" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $ps) { throw "docker compose ps failed" }
        Add-Line ""
        Add-Line '```text'
        foreach ($row in $ps) { Add-Line $row }
        Add-Line '```'
    }
}
Add-Line ""

# --- Health probes (mirrors scripts/health.ps1) --------------------------------
Add-Line "## Health probes"
Add-Line ""
$okCount = 0
$probeCount = 0
function Add-Probe([string]$Name, [bool]$Ok, [string]$Detail = "") {
    $script:probeCount++
    if ($Ok) { $script:okCount++ }
    $mark = "FAIL"
    if ($Ok) { $mark = "OK" }
    $suffix = ""
    if ($Detail) { $suffix = " - $Detail" }
    Add-Line ("- {0} {1}{2}" -f $mark, $Name, $suffix)
}

foreach ($p in @(
        @{ Name = "Port 3000 (web)"; Port = 3000 },
        @{ Name = "Port 8000 (api)"; Port = 8000 },
        @{ Name = "Port 5432 (postgres)"; Port = 5432 })) {
    $listening = Test-LocalPort -Port $p.Port
    $detail = "not listening"
    if ($listening) { $detail = "LISTENING" }
    Add-Probe -Name $p.Name -Ok $listening -Detail $detail
}

foreach ($t in @(
        @{ Name = "GET /api/health"; Url = "http://localhost:8000/api/health" },
        @{ Name = "GET /api/meta"; Url = "http://localhost:8000/api/meta" },
        @{ Name = "GET /api/health/stack"; Url = "http://localhost:8000/api/health/stack" },
        @{ Name = "GET web /"; Url = "http://localhost:3000/" })) {
    try {
        $r = Invoke-WebRequest -Uri $t.Url -UseBasicParsing -TimeoutSec $TimeoutSec
        Add-Probe -Name $t.Name -Ok ($r.StatusCode -ge 200 -and $r.StatusCode -lt 400) -Detail ([string]$r.StatusCode)
    }
    catch {
        Add-Probe -Name $t.Name -Ok $false -Detail $_.Exception.Message.Split("`n")[0]
    }
}
Add-Line ""
Add-Line ("**Probe summary: {0}/{1} OK**" -f $okCount, $probeCount)
Add-Line ""

# --- Deep stack JSON ------------------------------------------------------------
Invoke-Capture -Name "health/stack JSON" -Block {
    $stack = Invoke-RestMethod -Uri "http://localhost:8000/api/health/stack" -TimeoutSec $TimeoutSec
    Add-Line "## /api/health/stack"
    Add-Line ""
    Add-Line '```json'
    Add-Line ($stack | ConvertTo-Json -Depth 6)
    Add-Line '```'
    Add-Line ""
}

Invoke-Capture -Name "api meta" -Block {
    $meta = Invoke-RestMethod -Uri "http://localhost:8000/api/meta" -TimeoutSec $TimeoutSec
    if ($null -ne $meta.pipeline_mode) {
        Add-Line ("Pipeline mode: ``{0}``" -f $meta.pipeline_mode)
        Add-Line ""
    }
}

# --- DB counts (jobs / bug reports) ----------------------------------------------
Add-Line "## Job & report counts"
Add-Line ""
if ($dockerOk) {
    Invoke-Capture -Name "job counts" -Block {
        $rows = docker compose exec -T postgres psql -U streamclip -d streamclip -t -A -F " = " `
            -c "SELECT status, count(*) FROM jobs GROUP BY status ORDER BY status;" 2>$null
        if ($LASTEXITCODE -ne 0) { throw "psql jobs query failed (postgres container down?)" }
        $rows = @($rows | Where-Object { $_ -and $_.Trim() })
        if ($rows.Count -eq 0) { Add-Line "- Jobs by status: (none)" }
        else {
            Add-Line "- Jobs by status:"
            foreach ($row in $rows) { Add-Line ("  - {0}" -f $row.Trim()) }
        }
    }
    Invoke-Capture -Name "bug reports 72h" -Block {
        $cnt = docker compose exec -T postgres psql -U streamclip -d streamclip -t -A `
            -c "SELECT count(*) FROM bug_reports WHERE created_at > now() - interval '72 hours';" 2>$null
        if ($LASTEXITCODE -ne 0) { throw "psql bug_reports query failed" }
        Add-Line ("- Bug reports (last 72h): {0}" -f ([string]$cnt).Trim())
    }
}
else {
    Add-Line "- SKIP job/report counts - Docker not running"
}
Add-Line ""

# --- GitHub open beta bugs ---------------------------------------------------------
Invoke-Capture -Name "gh beta issues" -Block {
    $gh = Get-Command gh -ErrorAction SilentlyContinue
    if (-not $gh) { throw "gh CLI not installed" }
    $issues = gh issue list --label beta --state open --limit 50 --json number,title 2>$null | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw "gh issue list failed (auth?)" }
    Add-Line ("## Open GitHub issues labeled 'beta': {0}" -f @($issues).Count)
    foreach ($i in @($issues)) { Add-Line ("- #{0} {1}" -f $i.number, $i.title) }
    Add-Line ""
}

# --- OPERATOR FILL block (window-specific human facts) --------------------------------
Add-Line "---"
Add-Line ""
Add-Line ("## OPERATOR FILL - {0} window" -f $Label)
Add-Line ""
switch ($Label) {
    "T0" {
        Add-Line "Per-tester T0 outcomes (mirror into BETA_COHORT_EXIT.md section 3.1):"
        Add-Line ""
        Add-Line "| Tester id | Platform | T0-1 | T0-2 | T0-3 | T0-4 | Evidence |"
        Add-Line "|-----------|----------|------|------|------|------|----------|"
        Add-Line "| OPERATOR FILL | | | | | | |"
    }
    "H2" {
        Add-Line "- Testers with T0-1 pass (need >= 3): OPERATOR FILL"
        Add-Line "- Failures / blockers: OPERATOR FILL"
        Add-Line "- Mirror into BETA_COHORT_EXIT.md section 2 (H+2 row + detail table)."
    }
    "H24" {
        Add-Line "- Open P0 count: OPERATOR FILL"
        Add-Line "- Open P1 count: OPERATOR FILL"
        Add-Line "- Known-issues addendum published (yes/no/n-a): OPERATOR FILL"
        Add-Line "- Mirror into BETA_COHORT_EXIT.md section 2 (H+24 row + detail table)."
    }
    "H48" {
        Add-Line "- Backup on-call check-in done by: OPERATOR FILL"
        Add-Line "- Remaining P1s cleared or documented: OPERATOR FILL"
        Add-Line "- Mirror into BETA_COHORT_EXIT.md section 2 (H+48 row)."
    }
    "H72" {
        Add-Line "- Go/no-go decision (go / no-go / defer): OPERATOR FILL"
        Add-Line "- Rationale (1-3 sentences): OPERATOR FILL"
        Add-Line "- Unresolved P0 older than 7 days (none / list): OPERATOR FILL"
        Add-Line "- Signed by (Beta lead): OPERATOR FILL"
        Add-Line "- Mirror into BETA_COHORT_EXIT.md section 2 (H+72 detail) + section 5 gate 7."
    }
    default { throw "unhandled label $Label" }
}
Add-Line ""
Add-Line ("*Generated {0} by capture_phase0_evidence.ps1 - automated cells above are machine-captured; do not invent OPERATOR FILL values.*" -f $iso)

# --- Write file -------------------------------------------------------------------------
try {
    if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }
    $outPath = Join-Path $OutDir $fileName
    Set-Content -Path $outPath -Value ($lines -join "`r`n") -Encoding UTF8
}
catch {
    Write-Host ("FAIL could not write evidence file: {0}" -f $_.Exception.Message) -ForegroundColor Red
    exit 1
}

Write-Host ("Evidence written: {0}" -f $outPath) -ForegroundColor Green
Write-Host ("Probes OK: {0}/{1}" -f $okCount, $probeCount)
Write-Host "Next: fill the OPERATOR FILL block, then paste this path into docs/BETA_COHORT_EXIT.md."
exit 0
