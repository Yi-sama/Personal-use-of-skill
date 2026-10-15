---
name: v2rayn-proxy
description: Use this Windows computer's local v2rayN proxy when a website, download, Git HTTPS request, or API connection times out, fails to connect, or explicitly needs a proxy. Prefer the VLESS node US-owner-unlimited. Detect the real local port, verify the active node, and proxy only the task's local processes; do not change system proxy or TUN settings.
---

# Local v2rayN Proxy

Use the helper beside this skill, not a guessed proxy port. The user has authorized starting their installed v2rayN and selecting `US-owner-unlimited` when needed for an authorized network task. This is not permission to install clients, replace subscriptions, disable TLS verification, or change system proxy/TUN.

## Workflow

1. Run `Inspect` first. It reads configuration and SQLite metadata read-only and checks that the listener belongs to this installation's Xray/sing-box process. If the generated core configuration exists, it also checks its VLESS outbound against the named profile. If absent, `core_matches_expected` is `null`, not a claimed match; the configured node and runtime ownership are separate evidence. It does not connect to external websites or change v2rayN.
2. If not ready, the main agent may run `Ensure`. Record the original `active_node` first. `Ensure` can start the installed app hidden and, only when necessary, select the exact node through the app's Windows UI Automation controls. It never edits v2rayN's database or generated configuration directly. A node switch affects every process sharing that proxy; subagents must not switch nodes independently.
3. Run `Test` against the original public target or a suitable non-sensitive connectivity endpoint. Check the HTTP status, not only the listener. A 401/403/429 or captcha is not proof of a broken proxy; do not rotate nodes to bypass access controls. If the proxy also fails, report the actual result instead of repeatedly retrying.
4. Use `Run` for local commands. It sets proxy variables only on the child process and preserves the caller's environment. For clients that ignore these variables, use their documented explicit proxy option with the inspected endpoint.
5. Share the verified endpoint with subagents. Wait for their network work before restoring a node changed by this task. If a switch was needed, restore the original node at the end only if nobody else changed the node in the meantime. For an original VLESS node, use `Ensure -NodeName <original-name>`; otherwise restore through the app's UI. Do not close an app the user already had running.

## Commands

Resolve `<skill-dir>` to this skill's installed directory. Use PowerShell 7 (`pwsh`); Python 3's standard library and Windows `curl.exe` are required. The helper resolves an already running app, `-V2rayNPath`, `V2RAYN_PATH`, or `%LOCALAPPDATA%\Codex\v2rayn-proxy\settings.json`, in that order after an explicit argument.

```powershell
$helper = Join-Path '<skill-dir>' 'scripts\Invoke-V2rayNProxy.ps1'
& $helper -Mode Inspect
& $helper -Mode Ensure
& $helper -Mode Test -Url 'https://www.google.com/generate_204'
& $helper -Mode Run -FilePath 'git.exe' -CommandArgs @('ls-remote', 'https://github.com/OWNER/REPO.git', 'HEAD')
```

`Test` returns `transport_ok`, `http_status`, and `http_ok`. Do not equate an HTTP rejection with a TCP or TLS failure. `Run` refuses an incorrect/unverified node and preserves the child's exit code. `Inspect`/`Ensure` return only non-secret metadata. Do not print raw v2rayN configuration, UUIDs, subscription URLs, or private keys.

When a client needs an explicit setting, use the returned `http_proxy` or `socks_proxy`, for example `git -c http.proxy=<http_proxy> ...` or `curl.exe --proxy <http_proxy> ...`. Preserve a working SSH Git remote; HTTP proxy variables do not configure SSH.

## Boundaries

- Built-in hosted search/fetch tools and remote MCP servers do not inherit local process variables. Use an authorized local HTTP client or local browser with an explicit proxy setting when local egress is required; do not claim that cloud tools use this computer's node.
- `Run` supports executables, not arbitrary shell strings. Invoke `pwsh -File ...` explicitly for PowerShell scripts. Do not use `Invoke-Expression`.
- Never bind a new proxy listener to the LAN. Do not persist proxy variables or Git proxy settings globally.
- Local machine settings contain only `v2rayn_path`; keep them outside the shared skills repository.
- If the node is missing/ambiguous, Windows UI Automation is unavailable, or the app's controls differ, stop with the specific gap. Do not select a different node or fall back to another subscription.
- The Windows WPF selection adapter targets the observed v2rayN 7.18 controls. Unsupported layouts require inspection, not blind clicks or keystrokes.
