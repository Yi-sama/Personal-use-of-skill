# 案例 002：Windows 参数边界破坏 apply_patch 补丁

CASE-HASH: 75e0ba56ceb6

## 问题描述

当前环境没有独立暴露的 apply_patch API。PowerShell 中的 apply_patch 实际是 apply_patch.bat，内部使用百分号星号把参数转发给 codex.exe --codex-run-as-apply-patch。

多行补丁经过 Windows 批处理或 Windows PowerShell 5.1 原生命令参数边界时，可能出现两类不同问题：

1. 批处理无法稳定保留多行参数末尾，补丁程序认为最后一行不是结束标记。
2. 绕过批处理直接调用原生可执行文件时，补丁可能成功，但嵌入的双引号被参数序列化过程移除。

第二类问题尤其危险，因为退出码为零并不代表写入内容正确。

## 已验证环境

- Windows PowerShell：5.1.26100.4768
- apply_patch 入口：apply_patch.bat
- 底层入口：codex.exe --codex-run-as-apply-patch
- 测试内容：中文补丁测试，后接带双引号的 quoted

## 三路径实测

### 路径 A：通过 apply_patch.bat 传递多行参数

结果：失败，退出码为 1。

错误信息：Invalid patch: The last line of the patch must be '*** End Patch'

结论：批处理使用百分号星号重新拼接参数，不能作为可靠的多行补丁传输层。

### 路径 B：PowerShell 直接调用 codex.exe

结果：补丁成功，退出码为 0，但内容不保真。

- 期望：中文补丁测试 "quoted"
- 实际：中文补丁测试 quoted

结论：绕过批处理解决了换行问题，但 Windows PowerShell 5.1 的原生命令参数处理移除了嵌入的双引号。

### 路径 C：UTF-8 临时文件加 Python 参数数组

步骤：

1. 使用 UTF-8 无 BOM 把完整补丁写入临时文件。
2. Python 使用 encoding="utf-8" 读取补丁。
3. subprocess.run 使用参数列表传递底层可执行文件、模式参数和完整补丁字符串。
4. 检查退出码，并重新读取目标文件进行逐字符比较。

结果：退出码为 0，中文、换行和双引号全部精确保留，临时补丁文件无 BOM。

## 根因

本问题不是单纯的中文编码错误，而是命令参数传输层错误：

- BAT 的百分号星号会重新展开和拼接参数，无法可靠表达复杂多行字符串。
- Windows PowerShell 5.1 调用原生命令时会重新构造 Windows 命令行字符串。
- 引号既可能是数据，也可能被解释为参数分隔语法。
- 补丁程序最终接收到的字符串可能已经与原始补丁不同。

因此，即使补丁文本本身是合法 UTF-8，也仍可能在参数边界被修改。

## 强制规则

1. 不通过 BAT 或 CMD 的百分号星号转发多行补丁正文。
2. Windows PowerShell 5.1 下，不把含双引号、中文或复杂换行的完整补丁直接作为原生命令参数传递。
3. 当前环境缺少直接补丁 API 时，优先使用 UTF-8 无 BOM 临时文件加 Python subprocess 参数数组。
4. 调用成功后必须读取目标文件，比较关键内容；不能只检查退出码和 Success 文本。
5. 同时验证编码、换行、双引号、反斜杠和补丁结束标记。
6. 如果未来环境提供原生 apply_patch 工具 API，应优先使用工具 API，避免经过 shell 参数序列化。

## 推荐调用模式

Python 调用器的核心形式：

~~~python
patch = patch_path.read_text(encoding="utf-8")
result = subprocess.run(
    [str(executable), "--codex-run-as-apply-patch", patch],
    cwd=working_directory,
    check=False,
)
~~~

PowerShell 只负责使用 UTF-8 无 BOM 写入临时补丁文件，并把普通文件路径作为参数交给 Python，不再直接传递补丁正文。

## 验证标准

- apply_patch.bat 路径稳定复现补丁结束标记错误。
- PowerShell 直接调用路径稳定复现双引号丢失。
- Python 参数数组路径精确保留完整目标内容。
- 安全路径的补丁临时文件通过严格 UTF-8 解码且不含 BOM。
- 复现脚本最终输出 APPLY_PATCH_BOUNDARY_TEST=PASS。
