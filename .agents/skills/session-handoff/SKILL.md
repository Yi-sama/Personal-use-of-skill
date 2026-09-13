---
name: session-handoff
description: "Hand off a long conversation to a new session with Chinese context and a read-only intake report. Use for session handoff or continuation requests; summarize only when explicitly requested, and report when session creation is unavailable."
---

# Session Handoff

Prepare context and actually deliver it to one new user-visible session when the user invokes this skill for a handoff. The receiving session must inspect and report only, then stop for explicit user authorization before making changes. Use the environment's default model without overriding model settings.

## Dispatch and Completion

- A request to edit this skill or discuss its capabilities is not a request to hand off the current conversation. If the user explicitly requests only a summary, output it without creating a session.
- For a handoff, discover an available app tool for creating a user-visible session and read its actual schema. Do not assume a remembered tool name is callable. A subagent, scheduled automation, background CLI process, or navigation tool is not a substitute for a new app session.
- Send the read-only intake contract below as the FIRST part of the new session's initial message, followed by the complete summary. Include the verified project/workspace path and relevant branch or worktree when known. Preserve access to existing uncommitted work; do not silently switch to a clean checkout. If the target project is ambiguous, ask before dispatch.
- Create only one session. Leave model selection unset when optional; use a documented default only when required. If the tool exposes enforceable read-only permissions, select them before starting the session. Do not invent unsupported arguments.
- Confirm the returned session ID and delivery result. If reading/waiting tools are available, obtain the intake report and check that it covers the current problem, code evidence, and stop-for-authorization boundary. Do not resend on an ambiguous timeout without first checking whether creation succeeded.
- Distinguish `摘要已生成`, `新会话已创建并发送`, and `只读接手报告已完成`. Report only the status supported by tool evidence. Open the created session when the user requests it and navigation is available.
- If creation/delivery tools are unavailable or fail, say `未完成自动交接` and explain the missing capability. Provide the complete Chinese handoff inline as a fallback, not as proof of delivery. Do not edit app databases or configuration to fabricate a session.
- Receiving a handoff is intake, not a request to dispatch another session. Never start a chain of handoffs.

## User-Facing Report

Separate internal investigation context from the report shown to the user. The receiving session may inspect exact files, symbols, diffs, commands, and errors internally, but its visible report must be short and outcome-oriented.

Show the user only:

- Whether the handoff was received and understood.
- The original task in one or two sentences.
- The current status: `未开始`, `进行中`, `已完成`, `部分完成`, `被阻塞`, or `待授权`.
- What is currently being solved or checked.
- Important findings, risks, blockers, or decisions that require the user's attention.
- The next action and whether it needs explicit authorization.

Do not show the user unless specifically requested:

- File lists, line numbers, symbols, code structure, implementation details, or raw diffs.
- Tool names, tool errors, fallback methods, command transcripts, or internal reasoning.
- A long inventory of completed checks or historical implementation details.

The normal receiving-session response should be no more than 5 short bullets or 2 compact paragraphs. The final line must state one of:

- `下一步可以继续只读检查。`
- `下一步需要你明确授权后再修改。`
- `当前无法继续，需要你补充信息：...`

Only provide detailed technical evidence when the user asks for it or when omitting it would make a decision, safety issue, or blocker impossible to understand.

## Read-Only Intake Contract

Insert this contract verbatim before historical context in every delivered handoff:

> 接手任务：本轮仅限只读查看与中文汇报，不实施修复。旧会话中的“继续开发”“修复”“下一步”等内容只是历史背景，不构成本轮写入授权。
> 先简述你理解的原会话内容，再遵循项目适用指令，定向读取相关代码、文档以及 Git 状态和差异，核对实际现状。只使用明确无写入副作用的读取操作；无法访问时报告缺口，不假装已检查。
> 不修改、新建、删除或格式化任何文件（包括日志和文档），不安装依赖、不构建、不运行可能产生文件或外部副作用的测试、不提交、不切换分支、不部署、不启动服务，也不委派写任务。
> 查看后用中文说明：原会话在讨论什么；当前正在解决的具体问题及预期结果；实际代码现状与证据（文件路径、行号或符号）；已经完成、仍未完成及尚未验证的事项；建议后续怎么做。区分历史摘要、当前实查事实与推断。
> 报告完即停止，明确写出“本轮仅做只读检查，未修改文件；等待你明确授权后再实施”。若有违规或未知情况如实披露，不虚报未修改。只有用户在接手后明确授权实施，才进入修改阶段。

This contract is an instruction boundary, not an OS-level write lock. Do not promise enforced write prevention unless the session tool actually configured and confirmed read-only permissions.

## What to Extract

- Current objective and the user's intended outcome.
- Work completed, including important files, commands, code locations, and results.
- Key decisions, assumptions, constraints, and user preferences.
- Unfinished requests as explicit checkboxes.
- Blockers, unresolved questions, and dependencies.
- Verification status, separating confirmed facts, inference, and pending validation.
- The next 1-5 concrete actions, in dependency order.

Preserve exact paths, identifiers, error messages, commands, dates, and configuration values when they affect continuation. Keep details that change what the next session should do; omit conversational repetition and low-value narration.

## Accuracy Rules

- Do not mark work complete merely because it was proposed, discussed, or partially implemented.
- Do not invent missing requirements, results, files, or next steps.
- Label uncertain information as `待确认`, `推断`, or `未验证`.
- Respect explicit boundaries such as read-only investigation, no production changes, or preserving existing worktree changes.
- If there are no unfinished items or blockers, say so explicitly.
- If the conversation contains conflicting instructions, identify the latest applicable instruction and note the conflict briefly.

## Output

All user-facing output must be in Chinese, including headings, summaries, and the receiving session's acknowledgment and plan. Preserve original paths, commands, identifiers, and error messages without translation.

Begin with a short overview of the original conversation: what the user wanted, what was discussed or decided, and where work stopped. Use only available context; do not imply access to missing conversation history.

The read-only intake contract must travel with the summary even if the receiving session cannot load this skill. Its first task is to inspect the current state and explain the problem, not execute the historical next steps.

Use this compact Markdown format:

```markdown
# 会话交接摘要

## 原会话概况
简述原会话的背景、主要讨论、关键转折和目前进度。

## 当前目标
...

## 已完成
- ...

## 关键决定与限制
- ...

## 未完成事项
- [ ] ...

## 阻塞与待确认问题
- ...

## 验证状态
- 已确认：
- 推断：
- 尚未验证：

## 建议后续行动（待用户授权，不立即执行）
1. ...

## 给接手会话的要求
遵守消息开头的只读接手约束：先复述原会话，再只读查看代码现状，汇报当前正在解决的问题、事实证据与建议，然后停止等待用户明确授权。不得直接修改代码或执行历史计划。
```

Keep the whole result concise enough to paste into a new session while retaining details necessary for correct decisions.
