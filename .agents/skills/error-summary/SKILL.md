---
name: error-summary
description: >
  Consult a compact, evidence-backed library of Windows and Codex tool-error cases
  before a matching operation. Use permanent HASH keys to load only the relevant
  case, apply its verified method, and report tool failures without hiding impact.
---

# Error Summary

Use this skill when a task may match a known tool or environment failure, or when a new tool failure needs a reusable, evidence-backed case record.

## Startup protocol

1. Read the applicable project `AGENTS.md` files first; project and user rules take precedence.
2. Read `docs/ERROR-INDEX.md`.
3. Compare the task, environment, planned tools, and intended write content with the index triggers.
4. When a trigger matches, use its permanent HASH to read only the linked file in `docs/cases/`.
5. Follow the case's verified method before using a materially different method.
6. If no trigger matches, continue with normal engineering judgment without loading unrelated cases.

For FastCtx specifically, any planned call, including the first `read` or `grep`, matches `724f44f97dc7`. Read that detailed case before the first FastCtx call; do not first try `tools.mcp__fastctx__*` inside a generic JavaScript wrapper.

## Failure reporting

When a verified method fails, report the tool, attempted operation, exact error, file or task impact, evidence, and proposed alternative before changing approach. A successful later command does not erase an earlier failed tool call.

## Case maintenance

Add or change a case only when the failure and resolution have inspectable evidence. Each case needs a stable English canonical key, one permanent HASH, a compact index row, and a detailed document containing its trigger, confirmed failure, verified method, and verification criteria. HASH values are semantic lookup keys, not checksums; never modify or reuse an assigned HASH.

## Reference files

- `AGENTS.md`: local operating rules and error-library maintenance guidance.
- `docs/ERROR-INDEX.md`: compact permanent-HASH navigation index; read at task start.
- `docs/cases/`: detailed cases; read only after a matching trigger is identified.
