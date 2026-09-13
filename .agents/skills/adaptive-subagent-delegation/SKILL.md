---
name: adaptive-subagent-delegation
description: Use when the AI judges that a medium or large concrete task will materially benefit from subagents because of its breadth, complexity, risk, separable workstreams, substantial exploration, or need for independent verification. Small tasks should usually be handled directly. Once delegation starts, keep it in the execution strategy until the delegated work is completed, substantively replaced, or genuinely blocked; latency alone is never a reason to abandon it.
---

# Adaptive Subagent Delegation

## Core Principle

Decide autonomously whether subagents will materially improve the result.

Do not invoke delegation merely because a task includes file edits, repository reading, commands, or tests. Use it when the expected gain in quality, coverage, parallelism, specialization, or independent verification outweighs the coordination overhead.

"Mandatory" applies after delegation is chosen: once a subagent is started, honor that execution strategy. Do not abandon, duplicate, or take over delegated work merely because local execution appears faster.

## Activation Gate

Delegate when the task is medium or large and one or more of these signals is meaningful:

- It spans multiple files, components, systems, deliverables, or execution phases.
- It contains independent subtasks that can proceed in parallel.
- It requires substantial exploration before implementation or decision-making.
- It combines investigation, implementation, integration, and verification.
- It is risky enough to benefit from an independent review or verification pass.
- A bounded specialist assignment is likely to improve completeness or correctness.
- The user explicitly requests subagents, delegation, or parallel agent work.

Usually handle the task directly when:

- It is a short answer, explanation, lookup, or single command.
- It is one localized, low-risk edit with a focused verification step.
- The work is small enough that delegation would add more coordination than useful execution.
- There is no meaningful bounded subtask to assign.

Treat these as judgment factors, not mechanical thresholds. File edits, tests, repository reading, or multiple tool calls do not by themselves make delegation necessary. Turn count is also not a reliable measure of task size.

When uncertain, prefer direct handling for clearly small work and delegation for broad, risky, ambiguous, or multi-stage work.

## Classification Permission

Before deciding, the main agent may read the user request, applicable skills and instructions, `AGENTS.md`, project memory, task boundaries, and a small amount of readily available context. Keep this inspection limited to what is needed to judge scope and form useful assignments.

If understanding the task itself requires substantial exploration, that is a signal to delegate the exploration.

## Commitment Rule

Once the main agent starts one or more subagents:

1. Keep delegation as part of the task's execution strategy.
2. Before giving the final conclusion, bring every started assignment to an explicit terminal state: completed, legitimately canceled, or failed with the permitted fallback path exhausted.
3. Treat slow responses and wait timeouts as normal polling events, not failures.
4. Do not duplicate or take over an active subagent's scope solely to finish faster.
5. Continue only non-overlapping coordination, context gathering, integration preparation, review, or user communication while the subagent works.
6. If progress is unclear, check status or clarify the assignment.
7. If an assignment is too broad, narrow or split it while preserving delegated ownership.
8. If a result is substantively incorrect, reject it and request correction or reassign the scope.
9. Do not downgrade the remaining task to local-only execution because delegation was slower than expected.
10. Do not retroactively label an active assignment optional or unnecessary merely to avoid waiting for it.

Change or end a delegated assignment only when:

- The user changes direction or cancels the relevant scope.
- New evidence makes the delegated scope invalid or unnecessary.
- The result is substantively unusable and correction or reassignment is the better path.
- The agent or subagent tooling genuinely errors, becomes unavailable, or cannot proceed for a non-latency reason.

Latency alone never satisfies these exceptions. Repeated wait timeouts without an actual error still mean "continue tracking," not "fall back locally."

## Main Agent Workflow

1. Classify the task using scope, complexity, risk, separability, and expected delegation value.
2. If delegation is not justified, handle the task directly without apologizing for not using subagents.
3. If delegation is justified, create the smallest useful set of bounded assignments.
4. Give each subagent a clear outcome, scope, constraints, ownership boundary, and expected evidence.
5. Remind editing subagents that others may share the workspace and that unrelated work must be preserved.
6. Continue only non-overlapping work while assignments run.
7. Track delayed work through status checks, clarification, narrowing, or reassignment.
8. Review required results before accepting them.
9. Integrate findings or changes and make the final consistency judgment.

The main agent may perform small integration, conflict-resolution, or polish work. If integration reveals substantial new execution work and the overall task remains medium or large, delegate that new scope as well.

## Assignment Design

- Prefer the smallest number of subagents that provides a real benefit.
- Make assignments concrete and bounded enough that success is observable.
- Use parallel assignments only when their work is independent or has clear ownership boundaries.
- Avoid spawning several agents for work one bounded agent can handle well.
- Separate implementation and independent verification when risk justifies it.
- Do not delegate ceremonial work solely to claim compliance with the skill.

## Failure Handling

| Situation | Required response |
|---|---|
| Slow response or wait timeout | Continue coordinating and waiting. |
| Unclear progress | Request status or clarify the assignment. |
| Assignment too broad | Narrow or split it without taking over merely for speed. |
| Incorrect or incomplete result | Request correction or reassign the scope. |
| Agent error | Retry, narrow, or reassign to another subagent. |
| Tooling genuinely unavailable | Use a local fallback only if needed, and state why. |
| User changes direction | Cancel or replace only the affected delegated scope. |

## Decision Examples

| Situation | Likely decision | Reason |
|---|---|---|
| Explain one concept or answer a focused question | Direct | Coordination adds little value. |
| Make one obvious, localized, low-risk edit and run one focused check | Direct | Small scope with little separable work. |
| Trace behavior across several modules, implement a fix, and verify it | Delegate | Multi-stage work benefits from bounded exploration or verification. |
| Build a feature spanning UI, backend, and tests | Delegate | Multiple workstreams and integration risk. |
| Review a high-risk migration or security-sensitive change | Delegate | Independent scrutiny materially improves confidence. |
| Read one known file to answer a narrow question | Direct | Repository reading alone is not a trigger. |

## Anti-Rationalization Rules

Before delegation starts, do not force it onto a clearly small task merely because this skill exists.

After delegation starts, do not use any of these excuses to abandon it:

- "The subagent is taking too long."
- "I can probably finish its scope faster myself."
- "A wait call timed out, so the subagent must have failed."
- "I already have enough context to duplicate the work."
- "I will complete it locally and treat the subagent result as optional."

The correct response to latency is continued coordination. The correct response to actual failure is correction, narrowing, reassignment, or, only when delegation is genuinely unavailable, a disclosed local fallback.
