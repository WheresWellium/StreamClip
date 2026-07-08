# Package Phase 0 beta kit (BETA_GO_LIVE §5) into a distributable zip.
param(
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
$kitName = "streamclip-beta-kit-$suffix"
$stage = Join-Path $OutDir $kitName

New-Item -ItemType Directory -Force -Path $stage | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $stage "docs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $stage "scripts") | Out-Null

$files = @(
    @{ Src = "docs/BETA_TESTER_QUICKSTART.md"; Dst = "docs/BETA_TESTER_QUICKSTART.md" },
    @{ Src = "docs/BETA_TESTER_PLAN.md"; Dst = "docs/BETA_TESTER_PLAN.md" },
    @{ Src = "docs/BETA_KNOWN_ISSUES.md"; Dst = "docs/BETA_KNOWN_ISSUES.md" },
    @{ Src = "docs/CLEAN_VM_VERIFY.md"; Dst = "docs/CLEAN_VM_VERIFY.md" },
    @{ Src = "docs/BETA_OPS_PHASE0.md"; Dst = "docs/BETA_OPS_PHASE0.md" },
    @{ Src = "docs/distribution-runbook.md"; Dst = "docs/distribution-runbook.md" },
    @{ Src = ".env.example"; Dst = ".env.example" },
    @{ Src = ".env.production.example"; Dst = ".env.production.example" },
    @{ Src = "scripts/verify_stack.ps1"; Dst = "scripts/verify_stack.ps1" },
    @{ Src = "scripts/verify_coverage.ps1"; Dst = "scripts/verify_coverage.ps1" },
    @{ Src = "scripts/issue_beta_keys.py"; Dst = "scripts/issue_beta_keys.py" },
    @{ Src = "scripts/list_support_reports.py"; Dst = "scripts/list_support_reports.py" },
    @{ Src = "docker-compose.yml"; Dst = "docker-compose.yml" },
    @{ Src = "docker-compose.prod.yml"; Dst = "docker-compose.prod.yml" },
    @{ Src = "README.md"; Dst = "README.md" }
)

foreach ($f in $files) {
    $srcPath = Join-Path $root $f.Src
    if (-not (Test-Path $srcPath)) {
        Write-Error "Missing kit file: $($f.Src)"
    }
    Copy-Item $srcPath (Join-Path $stage $f.Dst) -Force
}

@"
StreamClip Phase 0 beta kit
Generated: $(Get-Date -Format o)
Commit: $commit
Tag: $(if ($Tag) { $Tag } else { "(none)" })

Contents match docs/BETA_GO_LIVE.md §5.
Setup: see docs/BETA_TESTER_QUICKSTART.md
Verify: .\scripts\verify_stack.ps1 (must exit 0 before first job)

Repo (canonical): https://github.com/WheresWellium/StreamClip
"@ | Set-Content (Join-Path $stage "KIT_README.txt") -Encoding utf8

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$zipPath = Join-Path $OutDir "$kitName.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zipPath -Force

Write-Host "Beta kit ready:" -ForegroundColor Green
Write-Host "  $zipPath"
Write-Host "  Staged folder: $stage"
