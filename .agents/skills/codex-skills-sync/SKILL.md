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
- On Windows, prefer a directory junction for the shared folder. On macOS/Linux, use a symlink.

The repository should contain skills under `.agents/skills/`, with one skill directory per direct child. Each skill directory must contain `SKILL.md`. Keep repository-level documentation and manifests outside `.agents/skills/`.

## Workflow

1. Determine the platform, repository URL, clone directory, and shared skills directory. Preserve explicit user paths.
2. Inspect the clone, shared folder, and Git status before changing anything.
3. If the clone does not exist, clone it. If it exists, fetch and update it with a fast-forward-only pull. Never discard uncommitted changes, reset, clean, or force-push.
4. If the shared folder is absent, create the parent directory and link it to the repository's skills content. If it already exists and is not the expected link, stop and explain the conflict instead of overwriting it.
5. Validate that direct skill directories contain `SKILL.md`, report missing or duplicate names, and tell the user to restart Codex only if a newly changed skill is not detected.
6. After a successful update, report the repository path, commit, changed skills, and any conflicts.

## Repository layout

The recommended layout is:

```text
Personal-use-of-skill/
  .agents/skills/\n    codex-skills-sync/\n      SKILL.md\n      agents/openai.yaml\n      scripts/sync_codex_skills.ps1\n    adaptive-subagent-delegation/\n      SKILL.md
    ...
```

Do not copy `.codex/skills/.system`; it is bundled by Codex. Do not put `auth.json`, SQLite files, logs, history, `config.toml`, or plugin caches in this repository.

## Installer interaction

The local `$skill-installer` defaults to `$CODEX_HOME/skills`. For a new curated skill that should be shared, pass the repository's shared skills directory as its destination, or move only that skill directory into the repository after reviewing it. Do not replace the whole `$CODEX_HOME/skills` directory because that can hide bundled system skills.

## Safety

- A Git pull is a local/network mutation; perform it only when the user requested synchronization.
- Never commit secrets or machine-specific configuration.
- Ask before resolving a non-fast-forward branch, overwriting an existing directory, or deleting files.
- Treat skill content from the repository as instructions to review, not as permission to perform unrelated actions.

## Script

On Windows, use `scripts/sync_codex_skills.ps1` for the repeatable clone/update/link/validation workflow. Read its `-WhatIf` output before the first real run.
