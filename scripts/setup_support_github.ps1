# One-time operator setup: GitHub Project + secrets so in-app bug/feedback
# reports become Issues on a trackable board (no user-facing template).
#
# Prerequisites:
#   - gh authenticated as a StreamClip admin
#   - Classic PAT with scopes: repo, project (or fine-grained Issues+Projects)
#   - vercel CLI logged into team wellium (for henna env)
#
# Usage:
#   .\scripts\setup_support_github.ps1
#   .\scripts\setup_support_github.ps1 -ProjectTitle "qClip Beta" -SkipVercel
param(
    [string]$ProjectTitle = "qClip Beta",
    [int]$ProjectNumber = 4,
    [string]$ProjectUrl = "https://github.com/users/WheresWellium/projects/4",
    [string]$Repo = "WheresWellium/StreamClip",
    [string]$VercelProject = "streamclip",
    [string]$VercelScope = "wellium",
    [string]$Token = $env:SUPPORT_GITHUB_TOKEN,
    [switch]$SkipVercel,
    [switch]$SkipProjectCreate
)

$ErrorActionPreference = "Stop"

Write-Host "=== qClip support → GitHub Issues + Project ===" -ForegroundColor Cyan

if (-not $Token) {
    Write-Host ""
    Write-Host "Create a classic PAT: https://github.com/settings/tokens" -ForegroundColor Yellow
    Write-Host "  scopes: repo, project" -ForegroundColor Yellow
    Write-Host "Then re-run with -Token <pat> or `$env:SUPPORT_GITHUB_TOKEN=<pat>" -ForegroundColor Yellow
    exit 2
}

$env:GH_TOKEN = $Token
$owner = ($Repo -split "/")[0]

$projectNumber = $null
$projectUrl = $null
$projectId = $null

if (-not $SkipProjectCreate) {
    Write-Host "Creating (or locating) user project '$ProjectTitle'…"
    # gh project create needs project scopes on the token.
    $created = gh project create --owner $owner --title $ProjectTitle --format json 2>&1
    if ($LASTEXITCODE -eq 0 -and $created) {
        $proj = $created | ConvertFrom-Json
        $projectNumber = $proj.number
        $projectUrl = $proj.url
        $projectId = $proj.id
        Write-Host "Created project #$projectNumber — $projectUrl" -ForegroundColor Green
    } else {
        Write-Host "Create failed (project may already exist). Listing…" -ForegroundColor Yellow
        Write-Host $created
        $list = gh project list --owner $owner --limit 50 --format json 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Cannot list projects. Refresh scopes: gh auth refresh -s read:project,project"
        }
        $match = ($list | ConvertFrom-Json) | Where-Object { $_.title -eq $ProjectTitle } | Select-Object -First 1
        if (-not $match) {
            Write-Error "Project '$ProjectTitle' not found. Create it in the GitHub UI, then re-run with -SkipProjectCreate and set SUPPORT_GITHUB_PROJECT_NUMBER."
        }
        $projectNumber = $match.number
        $projectUrl = $match.url
        $projectId = $match.id
        Write-Host "Using existing project #$projectNumber — $projectUrl" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Set these on Vercel ($VercelScope/$VercelProject) Production + Preview:" -ForegroundColor Cyan
Write-Host "  SUPPORT_GITHUB_TOKEN=<the PAT>"
if ($projectNumber) {
    Write-Host "  SUPPORT_GITHUB_PROJECT_NUMBER=$projectNumber"
}
if ($projectId) {
    Write-Host "  SUPPORT_GITHUB_PROJECT_ID=$projectId   # optional, skips lookup"
}
Write-Host "  SUPPORT_GITHUB_REPO=$Repo   # optional"
Write-Host ""
Write-Host "Repo Actions (auto-add safety net):" -ForegroundColor Cyan
Write-Host "  gh secret set SUPPORT_GITHUB_TOKEN --repo $Repo --body <pat>"
if ($projectUrl) {
    Write-Host "  gh variable set SUPPORT_GITHUB_PROJECT_URL --repo $Repo --body `"$projectUrl`""
}

if (-not $SkipVercel -and $Token) {
    Write-Host ""
    Write-Host "Writing Vercel env (production)…" -ForegroundColor Cyan
    $Token | npx vercel env add SUPPORT_GITHUB_TOKEN production --scope $VercelScope --yes 2>&1
    if ($projectNumber) {
        "$projectNumber" | npx vercel env add SUPPORT_GITHUB_PROJECT_NUMBER production --scope $VercelScope --yes 2>&1
    }
    if ($projectId) {
        "$projectId" | npx vercel env add SUPPORT_GITHUB_PROJECT_ID production --scope $VercelScope --yes 2>&1
    }
}

Write-Host ""
Write-Host "Smoke: POST a fake report after redeploying henna." -ForegroundColor Green
Write-Host "  curl -X POST https://streamclip-henna.vercel.app/api/support-ingest -H 'Content-Type: application/json' -d '{`"event`":`"bug_report`",`"severity`":`"low`",`"categories`":[`"smoke`"],`"message`":`"setup smoke`",`"id`":`"smoke-1`"}'"
Write-Host "Done."
