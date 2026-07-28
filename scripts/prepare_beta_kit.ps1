# Package Phase 0 beta kit (BETA_GO_LIVE §5) into a distributable zip.
param(
    [ValidateSet("Source", "ProdImages", "DocsOnly")]
    [string]$Mode = "Source",
    [string]$OutDir = (Join-Path (Split-Path -Parent $PSScriptRoot) "dist"),
    [string]$Tag = "",
    [switch]$IncludeInstaller
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$commit = (git rev-parse --short HEAD 2>$null)
if (-not $commit) { $commit = "unknown" }
$stamp = Get-Date -Format "yyyyMMdd-HHmm"
$suffix = if ($Tag) { $Tag } else { "$commit-$stamp" }
$kitName = "qclip-beta-kit-$Mode-$suffix"
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

function Resolve-WindowsInstaller([string]$StageDir, [string]$PreferredTag) {
    $installerName = "qClip-Setup-win-x64.exe"
    $installersDir = Join-Path $StageDir "installers"
    New-Item -ItemType Directory -Force -Path $installersDir | Out-Null
    $dest = Join-Path $installersDir $installerName

    $localPath = Join-Path $root "apps/desktop/release/$installerName"
    if (Test-Path $localPath) {
        Copy-Item $localPath $dest -Force
        Write-Host "Included Windows installer from local release build: $localPath"
        return $dest
    }

    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        Write-Error "IncludeInstaller: local installer missing at $localPath and 'gh' CLI not found. Build the installer or install GitHub CLI."
    }

    $repo = "WheresWellium/StreamClip"
    $tagsToTry = @()
    if ($PreferredTag) { $tagsToTry += $PreferredTag }
    $tagsToTry += @("v1.0.0-beta.5", "latest")

    $downloaded = $false
    foreach ($releaseTag in $tagsToTry) {
        Write-Host "Trying gh release download ($releaseTag) for $installerName ..."
        if ($releaseTag -eq "latest") {
            & gh release download -R $repo -p $installerName -D $installersDir --clobber 2>$null
        } else {
            & gh release download $releaseTag -R $repo -p $installerName -D $installersDir --clobber 2>$null
        }
        if ($LASTEXITCODE -eq 0 -and (Test-Path $dest)) {
            $downloaded = $true
            Write-Host "Included Windows installer from GitHub release $releaseTag"
            break
        }
    }

    if (-not $downloaded -or -not (Test-Path $dest)) {
        Write-Error "IncludeInstaller: could not resolve $installerName from local path or gh release download. Authenticate with 'gh auth login' (collaborator) or build apps/desktop/release first."
    }
    return $dest
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

$installerNote = ""
if ($IncludeInstaller) {
    $null = Resolve-WindowsInstaller -StageDir $stage -PreferredTag $Tag
    $macDmgName = "qClip-mac-arm64.dmg"
    $macLocal = Join-Path $root "apps/desktop/release/$macDmgName"
    $macDestDir = Join-Path $stage "installers"
    $macNote = ""
    if (Test-Path $macLocal) {
        Copy-Item $macLocal (Join-Path $macDestDir $macDmgName) -Force
        Write-Host "Included macOS DMG from local release build: $macLocal"
        $macNote = @"

macOS installer (Apple Silicon, no Docker)
------------------------------------------
This kit includes: installers/qClip-mac-arm64.dmg

1. Open installers/qClip-mac-arm64.dmg and drag qClip to Applications
2. If Gatekeeper blocks: right-click qClip.app → Open → Open
3. Paste your license key under Settings → License
"@
    } else {
        Write-Host "NOTE: macOS DMG not found at $macLocal — kit ships Windows installer only. Build on Apple Silicon: ./scripts/build_desktop_installer_macos.sh" -ForegroundColor Yellow
        $macNote = @"

macOS DMG: not included in this kit (build on Apple Silicon when ready).
"@
    }
    $installerNote = @"

Desktop installers (no Docker)
------------------------------
Windows: installers/qClip-Setup-win-x64.exe

1. Run installers\qClip-Setup-win-x64.exe
2. If Windows shows "Windows protected your PC" (SmartScreen): click More info → Run anyway
   (Unsigned beta builds trigger this; it does not mean the file is malware.)
3. Open qClip from the Start menu and paste your license key under Settings → License
$macNote
Note: GitHub anonymous download URLs for this private repo return 404.
Testers should use this kit zip (or Lemon Squeezy / operator Drive link), not the raw GitHub release URL.
Collaborators: gh release download v1.0.0-beta.5 -R WheresWellium/StreamClip -p "qClip-*"
"@
}

@"
qClip Phase 0 beta kit ($Mode)
Generated: $(Get-Date -Format o)
Commit: $commit
Tag: $(if ($Tag) { $Tag } else { "(none)" })

$runHint
$installerNote
Verify before first job: .\scripts\verify_stack.ps1 (exit 0)

Repo (canonical, collaborators): https://github.com/WheresWellium/StreamClip
"@ | Set-Content (Join-Path $stage "KIT_README.txt") -Encoding utf8

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$zipPath = Join-Path $OutDir "$kitName.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zipPath -Force

Write-Host "Beta kit ready ($Mode):" -ForegroundColor Green
Write-Host "  $zipPath"
Write-Host "  Staged folder: $stage"
if ($IncludeInstaller) {
    Write-Host "  Installer: $stage\installers\qClip-Setup-win-x64.exe"
}
