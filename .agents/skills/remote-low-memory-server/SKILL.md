---
name: remote-low-memory-server
description: "Safely administer a remote Linux server with about 1.6 GB RAM, especially Docker, deployment, and build tasks. Use only when explicitly invoked before making server changes."
---

# Remote Low Memory Server

Use this skill as an operational guardrail for a small remote Linux host. It is deliberately explicit-only: when invoked, follow these rules before changing the server.

## First: Observe

Use the configured SSH MCP connection (normally `ssh_remote`, connection `default`) and run read-only checks before any mutation:

```text
date; uptime; free -h; swapon --show; df -h /
docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
docker stats --no-stream 2>/dev/null || true
```

Record total/available RAM, swap, disk space, running containers, published ports, and any active build or package process. Do not ask for or display private keys, passwords, or complete access tokens.

## Hard Resource Rules

Treat a 1.6 GB RAM host as production-constrained:

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

End with: what changed, files/backups, services restarted, current RAM/swap, verification results, public ports/URLs, and any remaining risk. If a requested operation was unsafe for 1.6 GB RAM, say so plainly and provide the lower-memory alternative instead of silently attempting it.
