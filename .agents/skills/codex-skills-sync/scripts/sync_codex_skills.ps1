[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$RepoUrl = "https://github.com/Yi-sama/Personal-use-of-skill.git",
    [string]$RepoDir = (Join-Path $HOME "Documents\Codex\Personal-use-of-skill"),
    [string]$SharedSkillsDir = (Join-Path $HOME ".agents\skills"),
    [string]$RepoSkillsDir = "",
    [string]$GlobalAgentSource = "",
    [string]$GlobalAgentPath = (Join-Path $HOME ".codex\AGENTS.md"),
    [switch]$SyncGlobalAgent,
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

if ([string]::IsNullOrWhiteSpace($RepoSkillsDir)) {
    $RepoSkillsDir = Join-Path $RepoDir ".agents\skills"
}
if ([string]::IsNullOrWhiteSpace($GlobalAgentSource)) {
    $GlobalAgentSource = Join-Path $RepoDir "global\AGENTS.shared.md"
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

if ($SyncGlobalAgent) {
    if (-not (Test-Path $GlobalAgentSource)) {
        throw "Global Agent source does not exist: $GlobalAgentSource"
    }
    $overridePath = Join-Path (Split-Path -Parent $GlobalAgentPath) "AGENTS.override.md"
    if (Test-Path $overridePath) {
        throw "AGENTS.override.md takes precedence and was left untouched: $overridePath"
    }
    if (Test-Path $GlobalAgentPath) {
        $sourceHash = (Get-FileHash -LiteralPath $GlobalAgentSource -Algorithm SHA256).Hash
        $targetHash = (Get-FileHash -LiteralPath $GlobalAgentPath -Algorithm SHA256).Hash
        if ($sourceHash -ne $targetHash) {
            throw "Local global Agent differs from the repository baseline. No overwrite was performed: $GlobalAgentPath"
        }
        Write-Host "Global Agent already matches the repository baseline"
    } elseif ($PSCmdlet.ShouldProcess($GlobalAgentPath, "Copy shared global Agent from $GlobalAgentSource")) {
        $parent = Split-Path -Parent $GlobalAgentPath
        if (-not (Test-Path $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        Copy-Item -LiteralPath $GlobalAgentSource -Destination $GlobalAgentPath
        Write-Host "Installed shared global Agent: $GlobalAgentPath"
    }
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

Write-Host "Repository: $RepoDir"
Write-Host "Commit:     $(git -C $RepoDir rev-parse --short HEAD)"
Write-Host "Skills:     $($skillDirs.Count)"
$skillDirs | ForEach-Object { Write-Host "  - $($_.Name)" }
