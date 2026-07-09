# Package Phase 0 beta kit (BETA_GO_LIVE §5) into a distributable zip.
param(
    [ValidateSet("Source", "ProdImages", "DocsOnly")]
    [string]$Mode = "Source",
    [string]$OutDir = (Join-Path (Split-Path -Parent $PSScriptRoot) "dist"),
    [string]$Tag = ""
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$commit = (git rev-parse --short HEAD 2>$null)
if (-not $commit) { $commit = "unknown" }
$stamp = Get-Date -Format "yyyyMMdd-HHmm"
$suffix = if ($Tag) { $Tag } else { "$commit-$stamp" }
$kitName = "streamclip-beta-kit-$Mode-$suffix"
$stage = Join-Path $OutDir $kitName

if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $stage | Out-Null

function Copy-Rel([string]$RelPath) {
    $src = Join-Path $root $RelPath
    if (-not (Test-Path $src)) {
        Write-Error "Missing kit file: $RelPath"
    }
    $dest = Join-Path $stage $RelPath
    $destDir = Split-Path -Parent $dest
    if ($destDir -and -not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null
    }
    Copy-Item $src $dest -Recurse -Force
}

$alwaysFiles = @(
    "docs/BETA_TESTER_QUICKSTART.md",
    "docs/BETA_TESTER_PLAN.md",
    "docs/BETA_KNOWN_ISSUES.md",
    "docs/BETA_DOWNLOAD.md",
    "docs/CLEAN_VM_VERIFY.md",
    "docs/BETA_OPS_PHASE0.md",
    "docs/distribution-runbook.md",
    ".env.example",
    ".env.production.example",
    "scripts/verify_stack.ps1",
    "scripts/verify_coverage.ps1",
    "scripts/start_local.ps1",
    "scripts/issue_beta_keys.py",
    "scripts/list_support_reports.py",
    "docker-compose.yml",
    "docker-compose.prod.yml",
    "README.md",
    "mkdocs.yml"
)

foreach ($f in $alwaysFiles) { Copy-Rel $f }

if ($Mode -eq "Source") {
    $excludeDirs = @(
        ".git", "node_modules", ".next", "dist", "site", "workspace",
        ".pytest_cache", ".cache", "web/.next", "apps/desktop/release",
        "apps/desktop/.staging", "__pycache__"
    )
    $excludeNames = @("*.pyc", "*.pyo", ".env", ".env.local")

    Get-ChildItem -Path $root -Force | ForEach-Object {
        $name = $_.Name
        if ($excludeDirs -contains $name) { return }
        if ($name -eq "dist" -and $_.PSIsContainer) { return }
        $dest = Join-Path $stage $name
        if ($_.PSIsContainer) {
            robocopy $_.FullName $dest /E /XD $excludeDirs /XF $excludeNames /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
            if ($LASTEXITCODE -ge 8) { throw "robocopy failed for $name" }
        } else {
            Copy-Item $_.FullName $dest -Force
        }
    }
    $runHint = @"
Runnable source tree (Mode=Source).
Primary install: .\scripts\start_local.ps1
"@
} elseif ($Mode -eq "ProdImages") {
    Copy-Rel "scripts/prepare_beta_kit.ps1"
    $runHint = @"
GHCR / prod-compose path (Mode=ProdImages).
1. Copy .env.production.example to .env and set GHCR image tags + secrets
2. docker compose -f docker-compose.prod.yml pull
3. docker compose -f docker-compose.prod.yml up -d
4. .\scripts\verify_stack.ps1
"@
} else {
    $runHint = @"
Docs-only kit (Mode=DocsOnly) — NOT runnable alone.
Use Mode=Source (default) or clone https://github.com/WheresWellium/StreamClip
"@
}

@"
StreamClip Phase 0 beta kit ($Mode)
Generated: $(Get-Date -Format o)
Commit: $commit
Tag: $(if ($Tag) { $Tag } else { "(none)" })

$runHint

Verify before first job: .\scripts\verify_stack.ps1 (exit 0)

Repo (canonical): https://github.com/WheresWellium/StreamClip
"@ | Set-Content (Join-Path $stage "KIT_README.txt") -Encoding utf8

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$zipPath = Join-Path $OutDir "$kitName.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zipPath -Force

Write-Host "Beta kit ready ($Mode):" -ForegroundColor Green
Write-Host "  $zipPath"
Write-Host "  Staged folder: $stage"
