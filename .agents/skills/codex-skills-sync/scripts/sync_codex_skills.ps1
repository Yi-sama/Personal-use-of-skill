[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$RepoUrl = "https://github.com/Yi-sama/Personal-use-of-skill.git",
    [string]$RepoDir = (Join-Path $HOME "Documents\Codex\Personal-use-of-skill"),
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
        git -C $RepoDir pull --ff-only
    }
} else {
    $parent = Split-Path -Parent $RepoDir
    if ($PSCmdlet.ShouldProcess($RepoDir, "Clone $RepoUrl")) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
        git clone $RepoUrl $RepoDir
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
        }
    }
}

Write-Host "Repository: $RepoDir"
Write-Host "Commit:     $(git -C $RepoDir rev-parse --short HEAD)"
Write-Host "Skills:     $($skillDirs.Count)"
$skillDirs | ForEach-Object { Write-Host "  - $($_.Name)" }
if (-not $NoCodexLinks) {
    Write-Host "Codex:      $CodexSkillsDir"
}
