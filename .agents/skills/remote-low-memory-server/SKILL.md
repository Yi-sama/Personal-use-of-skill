---
name: remote-low-memory-server
description: "Inspect or administer the user's Chengdu server, US server, or both, selected explicitly by the user. Includes SSH routing and low-memory safeguards for Docker, deployment, and builds. Use only when explicitly invoked."
---

# Remote Low Memory Server

Use this skill for the user's Chengdu and US Linux servers. It is deliberately explicit-only. Selecting a server authorizes only the requested task: a request to inspect is read-only, and a request to read this skill alone does not authorize any connection.

## Select the Server Before Connecting

- Understand the user's Chinese or English selection of Chengdu, US, or both. If no target is clear from the current request/context, ask which server; never silently choose `default`.
- Chengdu means the existing domestic server. Its established connection is SSH MCP `ssh_remote`, connection `default`. Check the configured host mapping without exposing credentials before using it; a connection name alone is not proof of identity. If the mapping is missing or ambiguous, ask instead of guessing an IP.
- US means `156.238.252.115`, port `22`, user `root`, using the local private-key path `$HOME/.ssh/us-server-ed25519` on Windows (currently `C:/Users/liurunsen/.ssh/us-server-ed25519`). Do not use Chengdu's MCP `default` for the US server.
- Both means two explicitly identified targets. Keep commands, findings, backups, and resource decisions separate and label them by server. A failure on one host must not redirect its operation to the other.
- Do not copy credentials, application data, or configuration between hosts merely because both were selected. Do not create or overwrite SSH/MCP configuration unless that configuration change was requested.

### US Connection

Use local OpenSSH from PowerShell; no new MCP connection is required:

```powershell
ssh -p 22 -l root -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10 -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no -i "$HOME/.ssh/us-server-ed25519" 156.238.252.115
```

For agent-driven checks, append a bounded read-only remote command instead of leaving an interactive shell open. Retain normal host-key verification; never bypass a missing or changed host key. If the key is missing or locked, ask the user to make it available locally (for example through ssh-agent); do not request the private key or passphrase in chat, fall back to password guessing, or regenerate keys automatically.

The user reported successful US key login on 2026-09-19. This is setup history, not proof of current connectivity. US RAM, OS, services, and workloads must be observed rather than inferred from Chengdu.

## First: Observe

Use only the selected connection. First check `hostname`, `whoami`, and the connection endpoint against the selected target; stop on an identity mismatch. Then run read-only checks before any mutation:

```text
date; uptime; free -h; swapon --show; df -h /
docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
docker stats --no-stream 2>/dev/null || true
```

Run Docker checks only if Docker is installed; absence is a finding, not permission to install it. Record total/available RAM, swap, disk space, running containers, published ports, and any active build or package process. Do not ask for or display private keys, passwords, or complete access tokens.

## Hard Resource Rules

Chengdu was historically about 1.6 GB RAM; verify current capacity. Apply the numeric low-memory floor below to Chengdu or another similarly constrained host. For a larger US host, assess actual available memory and workload headroom instead of treating these small-host floors as sufficient. All other change and build safeguards apply to both:

- Keep at least 350 MiB available before starting work. Stop and reassess below 250 MiB, or when the kernel reports OOM kills.
- Never start `docker compose build`, `docker build`, `npm/pnpm/yarn install`, frontend production builds, `go build`, `cargo build`, or large package upgrades by default. Explain the estimated peak memory and obtain explicit confirmation first.
- Prefer an existing prebuilt image, release binary, external CI build, or a single-service restart. Avoid compiling frontend and backend together on the host.
- Do not pull large images or run multiple image pulls/builds in parallel. Check image size and disk space first.
- If a build is explicitly approved, serialize it, cap concurrency, set a timeout, and apply a memory limit where the tool supports it. Keep a live log and stop at the first sustained memory pressure.
- Do not add swap, change kernel settings, or resize services silently. These require a separate explanation and confirmation.

## Change Protocol

Before editing a file or restarting a service:

1. Inspect the active configuration and identify the owning process/container.
2. Back up the exact file or capture the current Compose/config state to a timestamped backup in the same directory.
3. State the change, expected resource impact, and rollback command.
4. Make the smallest reversible change. Restart only the affected service; do not recreate the whole stack unless required.
5. Verify immediately: process/container status, health check, local endpoint, ports, and recent logs.

Never use `docker system prune`, broad `apt upgrade`, recursive deletion, `git reset --hard`, or mass container removal as a first response. Ask before destructive or broad cleanup. Preserve user changes and unrelated containers.

## Docker Guidance

- Prefer `docker compose up -d <service>` for one service and inspect the resolved config with `docker compose config` first.
- Check actual container ports with `docker ps` and `docker inspect`; do not trust stale documentation or an old port mapping.
- Use service-level health checks and local `curl`/TCP probes before testing through a CDN, tunnel, or public DNS.
- Avoid exposing a service publicly unless the user explicitly requests it. If they do request it, call out that plain HTTP exposes credentials and require the corresponding cloud firewall/security-group rule.
- Do not assume containers can reach the host via its public IP. Test the Docker gateway or a shared network address; public-IP hairpinning may fail.

## SSH Failure / Recovery

If SSH becomes slow, refuses connections, or drops during a risky operation:

- Stop issuing retries and do not reboot blindly.
- Do not start another build, reinstall Docker, or delete containers to “recover” access.
- Report the last confirmed command and ask the user to use the provider console/serial terminal to check `free -h`, `dmesg -T | tail`, `systemctl status ssh`, and Docker state.
- Resume remote changes only after a stable SSH session and a fresh resource check.

## Completion Report

Label the report with the selected server(s). End with: what changed (or read-only/no changes), files/backups, services restarted, current RAM/swap, verification results, relevant public ports/URLs, and any remaining risk. Report unavailable measurements as unknown. If a requested operation was unsafe for a constrained host, say so plainly and provide the lower-memory alternative instead of silently attempting it.
