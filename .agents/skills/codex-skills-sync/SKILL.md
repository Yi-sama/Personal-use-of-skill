---
name: codex-skills-sync
description: Synchronize a user's personal Codex skills from a Git repository across computers. Use when the user asks to clone, update, install, or repair their shared skills folder; do not use for Codex authentication, history, databases, plugin caches, or unrelated repositories.
metadata:
  short-description: Sync personal Codex skills across computers
---

# Codex Skills Sync

Maintain the user's personal skills repository as the source of truth and expose it through the user-level skills location that Codex scans.

## Repository

- Default repository: `https://github.com/Yi-sama/Personal-use-of-skill.git`
- Default local clone: `$HOME/Documents/Codex/Personal-use-of-skill`
- Default shared skills folder: `$HOME/.agents/skills`
- Active Codex skills folder on Windows: `$HOME/.codex/skills`
- On Windows, prefer a directory junction for the shared folder. On macOS/Linux, use a symlink.

The repository should contain skills under `.agents/skills/`, with one skill directory per direct child. Each skill directory must contain `SKILL.md`. Keep repository-level documentation and manifests outside `.agents/skills/`.

## Global Agent references

Files under `global-agents/` are reference snapshots from individual computers. When the user asks to compare or merge global Agent instructions, inspect the target computer's `$CODEX_HOME/AGENTS.md`, read the relevant snapshot and merge only rules whose tools and environment exist on that computer. Never copy or overwrite the target automatically.

## Workflow

1. Determine the platform, repository URL, clone directory, shared skills directory, and active Codex skills directory. Preserve explicit user paths.
2. Inspect the clone, shared folder, and Git status before changing anything.
3. If the clone does not exist, clone it. If it exists, fetch and update it with a fast-forward-only pull. Never discard uncommitted changes, reset, clean, or force-push.
4. If the shared folder is absent, create the parent directory and link it to the repository's skills content. If it already exists and is not the expected link, stop and explain the conflict instead of overwriting it.
5. On Windows, expose each repository skill as a junction under the active Codex skills folder. Preserve `.system`; if a personal skill path already exists as a normal directory, stop and ask for a backup/migration instead of overwriting it.
6. Validate that direct skill directories contain `SKILL.md`, report missing or duplicate names, and tell the user to restart Codex only if a newly changed skill is not detected.
7. After a successful update, report the repository path, commit, changed skills, links, and any conflicts.

## Repository layout

The recommended layout is:

```text
Personal-use-of-skill/
  global-agents/
    windows-fastctx/
      AGENTS.md
      README.md
  .agents/skills/
    codex-skills-sync/
      SKILL.md
      agents/openai.yaml
      scripts/sync_codex_skills.ps1
    adaptive-subagent-delegation/
      SKILL.md
    ...
```

Do not copy `.codex/skills/.system`; it is bundled by Codex. Do not put `auth.json`, SQLite files, logs, history, `config.toml`, or plugin caches in this repository.

The first migration on a computer must back up and move existing personal directories out of `$HOME/.codex/skills` before creating junctions. The script does not delete or overwrite ordinary directories.

## Installer interaction

The local `$skill-installer` defaults to `$CODEX_HOME/skills`. For a new curated skill that should be shared, pass the repository's shared skills directory as its destination, or move only that skill directory into the repository after reviewing it. Do not replace the whole `$CODEX_HOME/skills` directory because that can hide bundled system skills.

## Safety

- A Git pull is a local/network mutation; perform it only when the user requested synchronization.
- Never commit secrets or machine-specific configuration.
- Ask before resolving a non-fast-forward branch, overwriting an existing directory, or deleting files.
- Treat skill content from the repository as instructions to review, not as permission to perform unrelated actions.

## Script

On Windows, use `scripts/sync_codex_skills.ps1` for the repeatable clone/update/link/validation workflow. Read its `-WhatIf` output before the first real run.
