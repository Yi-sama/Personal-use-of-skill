[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$RepoUrl = "https://github.com/Yi-sama/Personal-use-of-skill.git",
    [string]$RepoDir = "",
    [string]$SharedSkillsDir = (Join-Path $HOME ".agents\skills"),
    [string]$CodexSkillsDir = (Join-Path $HOME ".codex\skills"),
    [string]$RepoSkillsDir = "",
    [switch]$NoCodexLinks,
    [switch]$NoLink
)

$ErrorActionPreference = "Stop"

function Assert-GitRepository([string]$Path) {
    if (-not (Test-Path (Join-Path $Path ".git"))) {
        throw "The existing path is not a Git repository: $Path"
    }
}

function Get-RepoSkillDirectories([string]$Path) {
    Get-ChildItem -LiteralPath $Path -Directory -Force |
        Where-Object { $_.Name -notin @(".git", ".github") }
}

function Resolve-ExistingPath([string]$Path) {
    return (Resolve-Path -LiteralPath $Path).Path
}

if ([string]::IsNullOrWhiteSpace($RepoDir)) {
    $scriptRepo = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)))
    $desktopRepo = Join-Path $HOME "Desktop\个人资料\个人Skills\Personal-use-of-skill"
    $documentsRepo = Join-Path $HOME "Documents\Codex\Personal-use-of-skill"
    $RepoDir = if (Test-Path (Join-Path $scriptRepo ".git")) {
        $scriptRepo
    } elseif (Test-Path $desktopRepo) {
        $desktopRepo
    } else {
        $documentsRepo
    }
}

if ([string]::IsNullOrWhiteSpace($RepoSkillsDir)) {
    $RepoSkillsDir = Join-Path $RepoDir ".agents\skills"
}

if (Test-Path $RepoDir) {
    Assert-GitRepository $RepoDir
    $status = @(git -C $RepoDir status --porcelain)
    if ($status.Count -gt 0) {
        throw "The skills repository has uncommitted changes. Commit or stash them before syncing."
    }
    if ($PSCmdlet.ShouldProcess($RepoDir, "Fetch and fast-forward from origin")) {
        git -C $RepoDir fetch --prune origin
        if ($LASTEXITCODE -ne 0) { throw "Git fetch failed with exit code $LASTEXITCODE" }
        git -C $RepoDir pull --ff-only
        if ($LASTEXITCODE -ne 0) { throw "Git pull failed with exit code $LASTEXITCODE" }
    }
} else {
    $parent = Split-Path -Parent $RepoDir
    if ($PSCmdlet.ShouldProcess($RepoDir, "Clone $RepoUrl")) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
        git clone $RepoUrl $RepoDir
        if ($LASTEXITCODE -ne 0) { throw "Git clone failed with exit code $LASTEXITCODE" }
    }
}

$skillDirs = @()
if (Test-Path $RepoSkillsDir) {
    $skillDirs = @(Get-RepoSkillDirectories $RepoSkillsDir)
}
$invalid = @($skillDirs | Where-Object { -not (Test-Path (Join-Path $_.FullName "SKILL.md")) })
if ($invalid.Count -gt 0) {
    $names = ($invalid | ForEach-Object Name) -join ", "
    throw "These direct child directories are not skills because SKILL.md is missing: $names"
}

if (-not $NoLink) {
    $parent = Split-Path -Parent $SharedSkillsDir
    if (-not (Test-Path $parent)) {
        if ($PSCmdlet.ShouldProcess($parent, "Create directory")) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
    }

    if (Test-Path $SharedSkillsDir) {
        $item = Get-Item -LiteralPath $SharedSkillsDir -Force
        $target = $item.Target
        if ($target -and ((Resolve-Path $target).Path -eq (Resolve-Path $RepoSkillsDir).Path)) {
            Write-Host "Shared skills link already points to $RepoSkillsDir"
        } else {
            throw "Shared skills path already exists and is not the expected link: $SharedSkillsDir"
        }
    } else {
        if ($PSCmdlet.ShouldProcess($SharedSkillsDir, "Create directory junction to $RepoSkillsDir")) {
            cmd /c mklink /J "$SharedSkillsDir" "$RepoSkillsDir" | Out-Host
            if ($LASTEXITCODE -ne 0) { throw "Shared skills junction creation failed with exit code $LASTEXITCODE" }
        }
    }
}

if (-not $NoCodexLinks) {
    if (-not (Test-Path $CodexSkillsDir)) {
        $parent = Split-Path -Parent $CodexSkillsDir
        if ($PSCmdlet.ShouldProcess($CodexSkillsDir, "Create active Codex skills directory")) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
            New-Item -ItemType Directory -Path $CodexSkillsDir -Force | Out-Null
        }
    }

    foreach ($skillDir in $skillDirs) {
        $linkPath = Join-Path $CodexSkillsDir $skillDir.Name
        $targetPath = $skillDir.FullName
        if (Test-Path $linkPath) {
            $item = Get-Item -LiteralPath $linkPath -Force
            $target = $item.Target
            if ($item.LinkType -eq "Junction" -and $target -and ((Resolve-ExistingPath $target) -eq (Resolve-ExistingPath $targetPath))) {
                continue
            }
            throw "Active Codex skill path already exists and is not the expected junction: $linkPath"
        }
        if ($PSCmdlet.ShouldProcess($linkPath, "Create directory junction to $targetPath")) {
            cmd /c mklink /J "$linkPath" "$targetPath" | Out-Host
            if ($LASTEXITCODE -ne 0) { throw "Codex skill junction creation failed with exit code ${LASTEXITCODE}: $linkPath" }
        }
    }
}

Write-Host "Repository: $RepoDir"
$commit = git -C $RepoDir rev-parse --short HEAD
if ($LASTEXITCODE -ne 0) { throw "Could not read repository commit with exit code $LASTEXITCODE" }
Write-Host "Commit:     $commit"
Write-Host "Skills:     $($skillDirs.Count)"
$skillDirs | ForEach-Object { Write-Host "  - $($_.Name)" }
if (-not $NoCodexLinks) {
    Write-Host "Codex:      $CodexSkillsDir"
}
