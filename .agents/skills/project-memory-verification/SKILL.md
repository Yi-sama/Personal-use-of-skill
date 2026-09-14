---
name: project-memory-verification
description: >
  Establish and maintain project context from applicable AGENTS.md, README.md,
  SPEC.md, LOG.md, and LOG-INDEX.md files before coding, debugging, refactoring,
  documentation, or repository handoff work. Use this skill to protect existing
  changes, distinguish facts from inferences, record traceable project history,
  consult known-error cases before risky tool operations, report tool failures
  transparently, and perform separate specification and runtime/manual verification
  instead of claiming a change is fixed based only on AI reasoning or a passing test.
---

# Project Memory Verification

Use this skill for any non-trivial task inside an existing project. Its purpose is to make project work resumable by another AI and prevent an unverified "fixed" claim from becoming project history.

## Non-negotiable rules

1. **Read applicable `AGENTS.md` before project work.** Search from repository root to target path and read every applicable file from general to local. A deeper file overrides a shallower one when rules conflict. User instructions override project files. If no `AGENTS.md` exists, say so explicitly and use normal AI engineering judgment; do not invent project-specific rules.
2. **Read the compact known-error index at task start.** Read `references/error-index.md`, compare the current task and planned tool calls with its triggers, and load only matching case files by permanent HASH. Do not read every detailed case.
3. **Inspect before editing.** Identify repository root, read `git status`, inspect relevant diff, and locate target files and validation commands.
4. **Protect existing work.** Never discard, reset, clean, restore, or overwrite changes not made during this task. If the target overlaps existing edits, work from the current tree and report the overlap.
5. **Report every tool-call error transparently.** Tell the user what tool failed, what operation was attempted, what the error means, and whether it affected files or task state. If resolved, explain the verified resolution. If unresolved, explain attempted methods, remaining cause, impact, and required next action. Do not hide an earlier failure merely because a later workaround succeeded.
6. **Load memory selectively.** Read `README.md` for current orientation, `SPEC.md` for intended behavior and boundaries, `LOG-INDEX.md` for navigation, then only relevant `LOG.md` entries. Do not ingest a long log by default.
7. **Separate evidence types.** Label conclusions as facts, inferences, unknowns, or verified results. Historical logs do not automatically describe current behavior.
8. **Do not call work complete on AI assertion alone.** Separate specification validation, automated/runtime validation, and human/manual validation. If the human portion cannot be performed by the AI, mark it pending rather than implying it happened.
9. **Record completed work.** After a real change, add a concise traceable LOG entry and update `LOG-INDEX.md` when those files exist or the project uses them. Do not rewrite `README.md` as final current state until the user confirms the round is valid, unless explicitly asked.
10. **Confirm architectural changes.** Before changing architecture, technology stack, public contracts, persistent data shape, or project-wide conventions, stop and request user confirmation unless the user already authorized that exact change.

## Context discovery

Follow this order at the start of a task:

```text
1. Locate repository root and target path.
2. Find applicable AGENTS.md files.
3. Read AGENTS.md files from broadest scope to narrowest scope.
4. Read references/error-index.md and match planned operations to known cases.
5. Load only detailed error cases whose HASH triggers match the task.
6. Check git status and relevant diff.
7. Read README.md and SPEC.md when present.
8. Read LOG-INDEX.md when present.
9. Search LOG.md only for relevant dates, hashes, paths, or keywords.
10. Build a short project-memory summary before editing.
```

### Rule-file behavior

- If an applicable `AGENTS.md` exists and is readable, it is mandatory input.
- If several exist, apply nearest-directory precedence.
- If one is unreadable, report `context_partial`; continue read-only analysis, but do not perform a state-changing operation whose rules may be unknown.
- If rules conflict and precedence cannot resolve the conflict, report `context_conflicted` and ask before touching affected files.
- If no `AGENTS.md` exists, report `AGENTS.md: not found; normal project workflow used`. Infer commands only from repository evidence and label them inferred, not mandatory rules.

### Project-memory summary

Before editing, form this summary internally or show it when useful:

```text
Project purpose:
Current objective:
Applicable AGENTS.md:
README status:
SPEC status:
Relevant LOG-INDEX entries:
Relevant historical decisions:
Existing uncommitted changes:
Facts:
Inferences:
Unknowns:
Validation required:
```

## Known-error protocol

Treat known tool and environment failures as a searchable, extensible case system:

1. Read `references/error-index.md` at the beginning of a non-trivial project task.
2. Compare the task, environment, content being written, and planned tools with each compact trigger.
3. If a trigger matches, use its permanent HASH to open only the linked detailed case.
4. Follow the case's verified method before inventing another path.
5. If the verified method fails in the current environment, report that failure to the user before trying a materially different method. Explain the evidence, likely cause, proposed alternative, and risk.
6. If no trigger matches, continue with normal engineering judgment without loading unrelated cases.
7. Add a new case only after its failure mode and resolution have checkable evidence. Assign a stable English canonical key, derive one short permanent HASH, and never reuse or mutate that HASH.

The index is navigation, not a full log. Keep it compact and do not use dates or line numbers as case identifiers.

## Memory-file contract

Treat these files as a coordinated system:

| File | Answers | Use |
|---|---|---|
| `AGENTS.md` | How must the AI work here? | Operational rules and preferences; highest rule priority. |
| `README.md` | What is the project now? | Current purpose, setup, commands, structure, capabilities, limits. |
| `SPEC.md` | What should it become? | Goals, principles, boundaries, contracts, acceptance criteria. |
| `LOG.md` | How did it become this? | Chronological work, decisions, reasons, reproduction, verification. |
| `LOG-INDEX.md` | Where is the relevant history? | Compact index into LOG entries; never the full investigation. |

When names differ, discover documented equivalents instead of creating duplicate systems. Missing files are facts to report, not permission to silently invent a large documentation structure.

Use this evidence model:

- **Fact:** directly observed in current files, commands, tests, or explicit user instructions.
- **Inference:** reasoned from evidence; label it as an inference.
- **Unknown:** not established yet; define how it could be checked.
- **Verified:** supported by a repeatable check with recorded evidence.

For behavior conflicts, current reproducible code/test evidence describes what exists, `SPEC.md` describes what is intended, and logs describe historical context. For operation rules, applicable `AGENTS.md` and current user instructions win. Never silently resolve a material conflict.

## Pre-change protocol

Before changing code or project documentation:

1. Reproduce the reported behavior or establish a baseline when practical.
2. Identify the smallest affected file/module set.
3. Check whether intended files overlap pre-existing uncommitted edits.
4. State planned change, out-of-scope areas, risks, and validation plan.
5. Pause for confirmation if the change is architectural or covered by a project rule requiring confirmation.

Do not batch-format unrelated files, rename broadly, or clean up unrelated code.

## Dual verification

Verification has three distinct parts and they must be reported separately.

### Specification check (`spec_check`)

Confirm the change matches the user request, applicable `AGENTS.md`, `SPEC.md`, public contracts, compatibility constraints, and relevant decisions. Passing tests cannot compensate for violating intended design.

### Runtime/automated check (`runtime_check`)

Use the narrowest useful reproducible evidence first: regression test, unit/integration test, type check, lint, build, command-level reproduction, or API check. Record exact commands and outcomes. Do not treat a zero exit code as sufficient when the task has an observable output; inspect the actual changed file, generated content, parsed data, UI state, or other task-specific result. If a command was not run, state why.

### Human/manual check (`human_check`)

Ask the user to perform or confirm checks requiring human observation or an interactive environment, such as UI layout, visual quality, natural interaction, real business workflow, device behavior, or product intent. The AI must not claim this check passed unless it actually has an appropriate observable interface and performed it. Otherwise mark it `pending` and provide a concrete checklist.

Minimum final report:

```text
spec_check: pass | fail | unknown | blocked
runtime_check: pass | fail | partial | not_run | blocked | not_applicable
human_check: pass | fail | pending | not_applicable
overall: verified | partially_verified | failed | blocked | unverified
evidence: commands, observations, diff/worktree checks, and remaining risks
```

Use `verified` only when applicable specification and runtime checks pass, the scoped diff is understood, and human validation passes or is genuinely not applicable. Otherwise do not use that label.

## Logging protocol

After completed implementation or meaningful investigation, record:

```text
ID/date:
Objective or symptom:
Files and scope:
Change or investigation:
Decision and reason:
Reproduction/baseline:
spec_check:
runtime_check:
human_check:
Overall status:
Remaining risks or follow-ups:
Git commit/hash if available:
```

`LOG-INDEX.md` should contain one compact row per entry:

```markdown
| ID | Date | Topic | Scope | Status | LOG location | Hash |
|---|---|---|---|---|---|---|
| LOG-2026-001 | 2026-08-02 | Fix login redirect | auth | partially_verified | LOG.md:L120 | abc1234 |
```

Prefer stable IDs and exact line references or anchors. If the log grows large, search the index first and read only matching log sections. Do not log plans as completed work or include secrets.

## Final response contract

For a substantive task, report:

- Context: applicable `AGENTS.md`, memory files consulted, and worktree state.
- Change: what changed and which files were touched.
- Verification: exact commands, outcomes, manual checks, and anything not run.
- Tool errors: every failed tool call, its impact, resolution attempt, final status, and evidence that a successful recovery worked.
- Memory: LOG/LOG-INDEX updates and facts still unknown.
- Risks: remaining issues and the user's required manual confirmation.

For each tool error, report at least:

```text
Tool:
Operation:
Error:
Impact:
Resolution attempted:
Resolution result:
Verification:
Remaining action:
```

Prefer precise statuses over vague claims such as "should be fine", "looks fixed", or "tests mostly pass".

## Reference files

Read these only when the task needs their detail:

- `references/document-priority.md`: precedence, missing-file behavior, and conflict handling.
- `references/error-index.md`: compact permanent-HASH index; always read this file at task start.
- `references/error-0a8f92c4de0d.md`: UTF-8 text-writing case; read only when its trigger matches.
- `references/error-75e0ba56ceb6.md`: Windows multiline patch transport case; read only when its trigger matches.
- `references/error-5bd54090a30f.md`: restricted FastCtx traversal case; read only when its trigger matches.
- `references/error-ea543e17f995.md`: unavailable WMI/CIM process command-line case; read only when its trigger matches.
- `references/error-9c81d71b50e2.md`: optional OpenCV interpreter mismatch case; read only when its trigger matches.
- `references/error-724f44f97dc7.md`: FastCtx direct invocation, continuation, regex, and guarded replacement case; read only when its trigger matches.
- `references/verification-states.md`: state definitions and final-status rules.
- `references/templates.md`: copyable project-memory, log, index, and verification templates.
