# AI 工具调用防错必读

本文件是每个项目的 AI 必读入口。开始修改代码、调用补丁工具、写入中文或恢复压缩后的上下文之前，先阅读本文件。

## 启动顺序

1. 先读取本文件。
2. 查看下方错误索引，判断当前任务是否命中已知案例。
3. 命中后使用 HASH 精确搜索详细案例，不读取全部日志或全部案例。
4. 需要恢复项目状态时，只读取 docs/project-notes.md 和最新一份 docs/progress 文件。
5. 完成实际修改后，执行与变更类型相匹配的验证，不能只相信命令退出码。

### FastCtx 固定启动边界

根目录 `AGENTS.md` 和 `docs/ERROR-INDEX.md` 是启动引导文件，必须在任何其他项目读取前通过一次定向的普通 PowerShell/.NET 或 `rg` 读取完成；这两个文件明确豁免“优先 FastCtx”。完成引导后，正常使用顶层 FastCtx `read`、`grep` 或 `glob` 本身不再命中 `724f44f97dc7`，无需预读详细案例。

只有以下情况必须先按 HASH 读取 `docs/cases/error-724f44f97dc7.md`：准备使用 FastCtx `replace`；诊断 FastCtx 是否可用或调用边界；处理 `Partial`；处理路径、编码、glob、正则或替换保护诊断。FastCtx 只能通过顶层 MCP 边界调用，不能假定它存在于 `functions.exec`、`tools.*` 或其他通用包装器内。若顶层 FastCtx 不可用，可直接使用定向 PowerShell 或 `rg`；未实际调用失败时，这属于正常工具选择，不作为工具异常或启动顺序偏差写入用户报告。

调用前硬拒绝：FastCtx `read` 使用 `files` 批量形式时，不得同时传顶层 `limit`、`offset`、`encoding`、`pages`、`pdf_mode` 或 `view`；这些选项只能放在对应的单个文件项中，不确定时改用多个单文件读取。FastCtx `glob`/`grep` 不得从项目根目录配递归通配符，也不得主动进入 `runtime_data`、`work`、临时、缓存或 fixture 目录；未知目录先用定向 PowerShell/`rg` 建立已知范围。

## 已知错误索引

| HASH | 简要错误案例 | 正确使用方法 |
| --- | --- | --- |
| 0a8f92c4de0d | 写入中文时依赖 GBK、CP936 或系统默认编码，后续按 UTF-8 读取产生乱码 | 新建文本显式使用 UTF-8；写入后执行严格 UTF-8 解码与内容检查 |
| 75e0ba56ceb6 | 通过 Windows 批处理或 PowerShell 5.1 原生命令参数传递多行补丁，换行或双引号被破坏 | 将补丁写入 UTF-8 无 BOM 临时文件，用 Python 按 UTF-8 读取，再通过 subprocess 参数数组调用底层补丁执行器 |
| 5bd54090a30f | FastCtx 宽范围递归检查进入受限目录后无法获取预期证据 | 不修改权限；缩小到已知可访问子树或明确文件，并报告受限范围 |
| ea543e17f995 | WMI/CIM 的 Win32_Process 类不可用，无法查询 PID 完整命令行 | 记录 HRESULT；用 Get-Process 获取身份信息，并明确命令行不可用 |
| 9c81d71b50e2 | OpenCV 复核使用的 Python 环境缺少 cv2，导致不必要地跳过或误判 | 先确认项目解释器；普通任务不执行复验，不自行安装依赖 |
| 724f44f97dc7 | FastCtx 调用边界、`Partial`、参数诊断和安全替换 | 普通顶层读取无需预读；诊断异常或使用 `replace` 前读取案例，只调用顶层 `mcp__fastctx__*` |

精确搜索示例：

~~~powershell
rg -n -C 20 "75e0ba56ceb6" docs work
~~~

HASH 是永久检索键，不是随内容变化的文件校验和。创建后不得修改或复用。

## 强制规则：文本编码

1. 新建源码、配置、Markdown、JSON、YAML、脚本和普通文本时，显式使用 UTF-8。
2. 不使用 Default、OEM、GBK、CP936 或未声明编码的写入 API，除非外部遗留系统明确要求。
3. 修改已有文件前确认原编码，已有 UTF-8 文件保持 UTF-8。
4. Windows PowerShell 5.1 的 Set-Content -Encoding UTF8 会写入 BOM；需要无 BOM 时使用 System.Text.UTF8Encoding(false)。
5. chcp 65001 只改变控制台代码页，不能证明文件写入编码正确。
6. 写入后使用严格 UTF-8 解码重新读取，并检查目标中文、替换字符、BOM 和差异内容。

## 强制规则：apply_patch

1. 优先使用环境直接提供的 apply_patch 工具 API。
2. 如果 PowerShell 中的入口实际是 apply_patch.bat，且内部通过百分号星号转发参数，不把多行补丁正文直接传给它。
3. Windows PowerShell 5.1 下，不把包含中文、双引号、反斜杠或复杂换行的完整补丁直接作为原生命令参数传递。
4. 缺少直接工具 API 时，使用以下安全传输流程：
   - 使用 UTF-8 无 BOM 把补丁写入临时文件。
   - Python 使用 encoding="utf-8" 读取完整补丁。
   - subprocess.run 使用参数数组调用 codex.exe、--codex-run-as-apply-patch 和补丁字符串。
   - shell 只传递普通路径，不传递补丁正文。
5. 补丁返回 Success 或退出码零后，必须重新读取目标文件并检查实际内容。
6. 验证中文、换行、双引号、反斜杠和补丁结束标记均被精确保留。
7. 临时文件只作为补丁传输载体；目标文件仍必须由 apply_patch 修改。

## 测试与验证方法

收到新的常见错误后，按以下流程处理：

1. 建立隔离复现目录，避免影响真实项目文件。
2. 记录必要环境事实，例如操作系统、PowerShell 版本、默认编码和真实工具入口。
3. 构造最小失败样本，必须包含能暴露问题的字符或结构。
4. 运行错误路径作为负对照，记录退出码、标准输出、标准错误和实际生成内容。
5. 运行候选正确路径作为正对照。
6. 不只检查命令是否成功；逐字符或逐字节比较期望内容和实际内容。
7. 对文本执行严格 UTF-8 解码，并根据项目规范检查 BOM。
8. 对 JSON、YAML、源码和脚本继续运行解析器、编译器或语法检查。
9. 把结构化结果保存为 UTF-8 JSON，至少记录环境、错误路径结果、正确路径结果和布尔断言。
10. 让复现脚本在所有断言满足时输出明确的 PASS 标记，否则返回非零退出码。
11. 更新错误索引、详细案例和项目记录。
12. 用户阅读的总结只保留问题、证据、结论和正确方法，不附加内部工作区存储说明。

## 新案例收录规范

1. 为案例确定稳定的英文规范键。
2. 根据规范键生成一次短 HASH，建议使用 SHA-256 前 12 位。
3. HASH 写入本文件索引和详细案例标题附近。
4. 索引只保留 HASH、简要错误案例和正确使用方法。
5. 不在索引中记录日期和行号；日期不帮助语义检索，行号会随编辑漂移。
6. 详细案例记录问题、环境、复现、根因、错误路径、正确路径、强制规则和验证标准。
7. 每个结论必须有可运行测试或可检查证据。

## 上下文压缩后的恢复流程

如果对话被压缩、重新打开项目或无法确认之前做过什么：

1. 重新读取本文件。
2. 不直接读取完整日志。
3. 根据当前症状在本文件中选择 HASH。
4. 使用 rg 精确搜索 HASH，只读取命中案例附近内容。
5. 读取 docs/project-notes.md 获取长期决定和当前状态。
6. 只读取最新的 docs/progress/YYYY-MM-DD.md 获取最近完成工作。
7. 找到对应复现脚本，先查看断言，再决定是否重新运行。
8. 如果没有匹配 HASH，把问题作为新案例处理，不凭模糊记忆套用旧结论。

## 当前验证入口

- 编码问题：work/encoding-case-001/test-encoding.ps1
- apply_patch 参数问题：work/apply-patch-case-002/test-apply-patch-boundary.ps1
- FastCtx 受限目录问题：work/fastctx-case-003/test-fastctx-permission-boundary.ps1
- WMI/CIM 命令行问题：work/wmi-case-004/test-wmi-commandline-unavailable.ps1
- UTF-8 扫描：work/check_utf8.py

后续新增问题时持续更新本文件，但保持索引和规则简洁。详细证据留在按 HASH 可检索的案例文档中。
