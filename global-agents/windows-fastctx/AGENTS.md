## Mandatory Error Summary startup gate

For every task that inspects, searches, edits, or runs checks against local files:

1. The first local-file operation is a bootstrap exception: use one targeted ordinary PowerShell/.NET or `rg` read to load `C:\Users\liurunsen\Desktop\个人资料\个人Skills\Error Summary\AGENTS.md` and its `docs/ERROR-INDEX.md`. Do not use FastCtx for these two bootstrap files.
2. Match cases by the concrete operation or observed failure. Planning an ordinary direct FastCtx `read`, `grep`, or `glob` call does not by itself trigger case `724f44f97dc7`.
3. Read case `724f44f97dc7` before FastCtx `replace`, or when diagnosing FastCtx availability, invocation, `Partial`, path, encoding, glob, regex, or replacement diagnostics.
4. FastCtx is optional. When used, call only the direct top-level `mcp__fastctx__read`, `mcp__fastctx__grep`, `mcp__fastctx__glob`, or `mcp__fastctx__replace` tools. Never call it through `functions.exec`, `tools.*`, or another generic wrapper.
5. If direct FastCtx is unavailable, use targeted PowerShell or `rg`. This normal fallback is not a tool incident unless a FastCtx call actually failed; do not add a user-facing startup-order warning for a compliant bootstrap or fallback.
6. Do not recursively enumerate an entire project with FastCtx; use known files or a narrow path.
7. Batch-read shape is strict: when a FastCtx `read` request contains `files`, omit top-level `limit`, `offset`, `encoding`, `pages`, `pdf_mode`, and `view`; put per-file options only inside each `files` item. If uncertain, use separate direct reads.
8. Scope veto: never call FastCtx `glob` or `grep` from a project root with a recursive wildcard, and never intentionally enter `runtime_data`, `work`, temp, cache, or fixture directories. Inventory unknown trees with targeted PowerShell or `rg` first, then use a known accessible subtree.

<!-- fastctx:begin -->
## Local file inspection

After the two-file bootstrap above, for reading, searching, and finding local files, prefer the FastCtx MCP
tools — `mcp__fastctx__read`, `mcp__fastctx__grep`, `mcp__fastctx__glob` —
over `cat`/`Get-Content`, `rg`/`findstr`/`Select-String`, and `dir`/`ls -R`.
Read only what the task needs. When you need several files, pass them to
one read call as files=[{"path": ...}, ...] instead of one call per file.
Pass absolute paths. The last line of every result says `Complete` or
`Partial` — continue only with the exact parameters a `Partial` note
provides.

### Batch replacement

Use `mcp__fastctx__replace` for mechanical find-and-replace across files.
It preserves each file's encoding and line endings, supports dry-run previews,
and rejects concurrent changes before writing. Use apply_patch for generated
content, semantic rewrites, or small local edits.
<!-- fastctx:end -->
## Subagent 编排

Subagent 用于把宽而重的探索与核验从主线程隔离，减少上下文膨胀和上下文腐烂，让根 Agent 保留足够注意力完成方案取舍与最终验证。它还能提供独立视角进行交叉核验；当任务彼此独立时，可通过并发缩短整体完成时间。

本节的适用对象是根 Agent。Subagent 按委托执行；只有委托明确授权时，才在父任务范围内派生下级 Agent。

### 自主委派硬约束

- 根 Agent 直接处理已知位置的小任务、单一事实、即将修改的确切代码和奠基性文档。
- 接到复杂任务后，先读取适用指令、项目入口和任务直接相关的必要文件，形成基础认识并划定互斥探索边界；初读到此完成，需要大范围探索时再交给 `explorer`。
- 仅在能明确减少主线程上下文负担或提供独立核验时自主委派。一个 Subagent 足以完成时只委派一个；仅当需要多个 Subagent，且任务边界清晰、彼此独立并确有并行收益时并发。
- 完成本轮必要派发并记录全部目标后，立即使用 `wait_agent`；每次被结果唤醒后继续等待，直到所有目标均 `complete`、`blocked`、`failed` 或已中止。等待期间停止其他分析、检索、命令执行和文件修改；只有用户明确要求等待期间处理其他工作时，才按其要求执行。
- 不因“彻底”“多角度”等措辞扩大委派；不把综合判断整体外包，也不重复 Subagent 已执行的同一搜索。

### 角色与委托

- 按任务选择 `explorer`、`reviewer`；无专职角色匹配时使用 `default`。
- Subagent 默认只承担探索与核验；只有委托明确授权时才实施代码修改。
- 并行委托必须按互斥问题域拆分；每个 directive 明确唯一问题、输入范围、排除项和交付物。边界无法清晰划分时，合并任务或由根 Agent 处理。
- 每个委托必须自包含：目标、必要背景与已有结论、范围、具体问题、权限、禁止事项、成功标准和期望证据。
- 精确结论要求 `file:line`、符号名或来源链接；写任务还必须给出精确文件所有权和所需验证。
- Subagent 每次报告统一包含 `status: complete | blocked | failed`、`summary`、`evidence` 和 `gaps`。

### Fresh Agent 与执行模式

- 新建独立 Agent 时必须显式使用 `fork_turns="none"`；委托遵守上述自包含契约。
- 仅当目标和范围不变，且复用已读文件、工具结果或失败上下文能显著减少重做时，使用 `followup_task` 续接原 Agent；不得借续接改派新任务。方向变化、独立复核、错误方案推倒重做或无关任务使用 Fresh Agent。
- 并发任务及下级派生不得超过当前可用并发槽位。状态跟踪只由根 Agent 完成：不得派生“监工 Agent”，不得循环调用 `list_agents` 探测进度、使用 `sleep` 等待或发送催促消息。Agent 未返回终态前，不推测、不综合，也不向用户宣称其结果。

### 复杂任务的 Coordinator 流程

仅当任务包含研究、实施或独立验证组成的多阶段链路时采用以下流程；简单任务由根 Agent 直接完成。

1. **Research**：按前述委派门槛使用 `explorer` 侦察，返回结论与定位，不倾倒原始材料；仅在任务相互独立且有实际收益时并发。
2. **Synthesis**：根 Agent 点验关键证据，形成方案、边界、依赖顺序和可执行规格。
3. **Implementation**：根 Agent 负责实施；确需委派写任务时，明确授权 `default` 并按互斥文件范围拆分，不调用 `worker`。
4. **Verification**：根 Agent 核查实际 diff、测试和高风险行为；重要结论或高风险修改可交给 Fresh `reviewer` 独立复核。
5. **Relay**：根 Agent 综合事实、验证结果、风险和未确认项，向用户报告最终结果。

### 并发写入

- `explorer`、`reviewer` 只读；`default` 仅写入明确授权的互斥文件范围。
- 每个写任务都要说明其他 Agent 可能并行修改；禁止覆盖、回滚或顺手修复他人及范围外工作。
- 多个任务会修改同一文件时，重新切分、串行执行或由根 Agent 处理；发生陌生变更、所有权重叠或冲突时停止并报告。

### 生命周期与失败

- 每个 Agent 默认一个初始 directive、一次完整报告后停止；受限续接必须保持原目标和范围，不得改派。用户改变目标时，对每个不再相关的活动目标调用 `interrupt_agent`。
- 有合理假设即可继续；只有确需用户动作或外部状态变化时才报告 `blocked`，并在 `gaps` 中写明精确需要。
- 结果有缺口时，同目标、同范围且旧上下文有价值则受限续接；否则根 Agent 自行补查，或创建更小的自包含 Fresh 任务。同一失败策略最多重试一次。

### 验收与转述

- Subagent 报告是待点验证据，不是完成证明；根 Agent 必须核对关键定位、实际改动、检查结果和可观察行为。
- 根 Agent 完整阅读即将修改的代码和奠基性文档，负责方案取舍、最终验证与用户沟通。
- 根 Agent 始终向用户提供自包含结论，只转述经点验的事实、结果、风险和缺口；原始日志、Subagent 计划及自述仅作为内部核验材料。

## 项目记忆与错误案例

对于现有项目中的实质性工作，必须使用 `project-memory-verification` skill。实质性工作包括：查看或分析项目文件、修改代码、排查和修复 bug、重构、编写或修改测试、修改配置、项目文档、代码审查、构建、发布和交接。

普通闲聊、一般知识问答、无需查看项目文件的讨论、翻译和纯头脑风暴，不需要使用该 skill。若对话从闲聊转为具体项目任务，必须在进行任何项目操作前启用该 skill。

在查看项目文件、运行项目相关命令或修改任何文件之前，必须先阅读 `C:\Users\liurunsen\Desktop\个人资料\个人Skills\Error Summary`，必须逐项比对当前任务、运行环境、将要写入的内容和计划调用的工具；凡是触发条件匹配的错误案例，都必须通过其永久 HASH 打开并阅读详细案例，遵循其中已验证的方法。不得因任务看似简单而跳过错误案例检查。

处理缺陷时，必须定位并记录从症状到根本原因的因果链。除非用户明确接受为临时缓解措施，否则不得将兜底、重试、忽略错误、抑制报错、仅改测试或其他绕过方式宣称为修复。必须验证根因不再复现；可行时补充回归测试。
