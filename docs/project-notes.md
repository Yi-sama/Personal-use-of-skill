# Project Notes

## Current Status

- Personal skills are maintained under `.agents/skills/`; this computer's shared `.agents/skills` folder and individual `.codex/skills` entries use junctions.
- This computer's `$HOME/.codex/AGENTS.md` is a symbolic link to `global-agents/windows-fastctx/AGENTS.md`; changing the global trigger also changes that tracked file, without replacing the link.
- `v2rayn-proxy` provides local Windows proxy inspection, preparation, target testing and child-process execution. Do not commit or push other pending changes as part of its installation.
- `remotion-best-practices` is the official aggregate Remotion skill, imported from `remotion-dev/skills`; update it from upstream as a complete directory so its routed references stay consistent.

## Environment

- Verified on 2026-10-15 with Windows, PowerShell 7, Python 3 standard library, curl and v2rayN 7.18.
- Local machine discovery settings live outside this repository at `%LOCALAPPDATA%\Codex\v2rayn-proxy\settings.json`.
- Preferred node: `US-owner-unlimited` (VLESS). This computer's observed mixed listener was `127.0.0.1:30000`; always rediscover it.
- The configured node, listener process ownership and generated-core evidence are reported separately. Generated config was observed to disappear while Xray kept listening; the reason is not established. Missing generated config is reported as unknown core evidence, not as a confirmed match.

## Commands

- `python -B tests/test_v2rayn_proxy.py -v`
- `pwsh -NoProfile -File tests/v2rayn-proxy.ps1`
- `pwsh -NoProfile -File .agents/skills/v2rayn-proxy/scripts/Invoke-V2rayNProxy.ps1 -Mode Inspect`

## Decisions

- Only the main agent manages node changes; child commands receive process-scoped proxy variables. Do not change system proxy/TUN or bypass TLS checks.
- SQLite access is read-only and explicitly closed. No subscription or credential data is printed.
- Windows UI Automation targets the observed profile grid and Enter activation behavior. Text/cell matches are deduplicated by row runtime ID.
- Cold startup and actual cross-node activation remain untested on the live client; avoid disrupting a working connection merely to exercise them.
