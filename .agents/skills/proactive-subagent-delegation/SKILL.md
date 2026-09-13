---
name: proactive-subagent-delegation
description: Use when the user gives a clear actionable task that may involve research, implementation, review, verification, or multi-step execution, especially when bounded subtasks can be delegated to sub-agents in parallel. Skip only for truly tiny tasks or when no safe, useful sub-agent action exists.
---

# Proactive Subagent Delegation

## Overview

Treat clear user tasks as opportunities to delegate. Unless an exception applies, proactively spawn at least one sub-agent before doing the bulk of the work locally.

## Core Rule

When the user gives a concrete task with an intended outcome, proactively call a sub-agent. Do this before the main body of execution, not as an afterthought.

## Decision Flow

1. Decide whether the user request is a clear actionable task.
2. If yes, identify the immediate local step you should keep on the critical path.
3. Identify at least one bounded subtask that materially advances the goal without duplicating your local step.
4. Spawn a sub-agent for that bounded subtask.
5. If there are multiple independent subtasks with disjoint scopes, spawn multiple sub-agents in parallel.
6. Continue non-overlapping local work while they run.
7. Integrate, verify, and close the loop.

## What Counts As A Clear Task

Use this skill when the user is asking Codex to do something concrete, such as:
- inspect, search, debug, implement, refactor, review, verify, summarize, compare, or prepare deliverables
- modify code or files
- investigate a bug or failure
- gather information from a codebase or workspace

Do not rely on the task being large. If it is a real task with a concrete objective, bias toward delegation.

## Delegation Rules

- Delegate proactively, not only after getting stuck.
- Prefer one sub-agent minimum for clear tasks.
- Prefer parallel sub-agents when subtasks are independent.
- Keep the immediate blocking critical-path step local when waiting would stall progress.
- Give each sub-agent a concrete goal, tight scope, and explicit output format.
- For code changes, assign clear file or responsibility ownership.
- Tell coding sub-agents they are not alone in the codebase and must not revert others' edits.
- Do not delegate the exact same unresolved subtask twice.
- Do not spawn sub-agents with vague prompts like "look around" or "handle this somehow".
- Keep final synthesis, validation, and the user-facing answer in the parent agent.

## Allowed Exceptions

You may skip proactive delegation only when at least one of these is true:
- The task is truly tiny and single-step, and delegation would add more overhead than value.
- No safe or appropriate sub-agent action exists in the current environment.
- The only possible subtask is the exact immediate blocking step you must do locally right now, and there is no useful sidecar task to run in parallel.
- The user explicitly asks for direct handling only or forbids delegation.

When using an exception, say so explicitly and briefly.

## Red Flags

If you notice these thoughts, stop and delegate:
- "I can just do this myself first."
- "I'll call a sub-agent only if I get stuck."
- "This task is probably too small to delegate."
- "I'll finish the core work, then maybe ask a sub-agent to review."
- "I don't have parallel work, so I should skip delegation entirely."

These usually indicate you are reverting to a non-delegating default.

## Response Pattern

At the start of task execution:
- State the goal briefly.
- State what you will handle locally first.
- State which sub-agent task you are dispatching.

During execution:
- Keep working on non-overlapping local steps while the sub-agent runs.
- Wait only when the delegated result is genuinely needed for the next critical-path decision.

At completion:
- Integrate the delegated output.
- Verify the combined result.
- Mention any exception if you intentionally skipped delegation.
