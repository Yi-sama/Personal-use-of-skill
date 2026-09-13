# 案例 001：中文文本被 GBK 写入后乱码

CASE-HASH: 0a8f92c4de0d

## 问题描述

AI 编码或调用命令行工具写入中文时，如果依赖 Windows 中文环境的默认编码，内容可能按 GBK/CP936 写入；项目、编辑器、补丁工具或后续程序通常按 UTF-8 读取，于是出现乱码、替换字符或解码失败。

## 已验证环境

- Windows PowerShell：`5.1.26100.4768`
- 系统默认编码：`gb2312`
- 控制台输出编码：`utf-8`
- Python 标准输出编码：`gbk`
- Python 文件系统编码：`utf-8`

这说明同一进程链路内可以同时存在多种编码默认值，不能从“终端能显示中文”推断“文件是 UTF-8”。

## 复现方法

运行：

```powershell
& '.\work\encoding-case-001\test-encoding.ps1'
```

测试文本为：`中文编码测试：你好，世界！`

验证结果：

- GBK 字节数：`26`
- UTF-8 字节数：`39`
- GBK 按 GBK 解码可以正常往返，但按 UTF-8 宽松解码得到 `���ı�����ԣ���ã����磡`
- 严格 UTF-8 解码器拒绝 GBK 字节
- UTF-8 写入与严格 UTF-8 读取往返成功
- 测试使用 UTF-8 无 BOM 文件，结果为 `ENCODING_TEST=PASS`

原始结果保存在 `work/encoding-case-001/artifacts/result.json`。

## 根因

错误不是“中文本身不兼容”，而是写入端与读取端采用了不同编码：

1. 写入端依赖系统区域设置、PowerShell 5.1、Python locale 或原生命令的默认编码。
2. 读取端按现代项目惯例使用 UTF-8。
3. GBK 字节序列不是合法的 UTF-8 字节序列，严格解码失败；宽松解码会插入 `�`。

## 强制规则

1. 新建源码、配置、Markdown、JSON、YAML、脚本和普通文本时，默认显式写为 UTF-8。
2. 不得使用 `Default`、`OEM`、GBK、CP936 或未声明编码的文本写入 API，除非目标格式明确要求。
3. 修改已有文件前先确认原编码；已有 UTF-8 文件必须保持 UTF-8。
4. 只有外部遗留系统明确要求 GBK 时才可使用 GBK，并在边界处显式转码和测试。
5. 写入中文后必须执行严格 UTF-8 解码验证，并检查实际文本或差异。

## 推荐写法

### Python

```python
from pathlib import Path

Path("example.txt").write_text("你好，世界！", encoding="utf-8", newline="\n")
text = Path("example.txt").read_text(encoding="utf-8")
```

### PowerShell 7+

```powershell
Set-Content -LiteralPath '.\example.txt' -Value '你好，世界！' -Encoding utf8NoBOM
```

### Windows PowerShell 5.1

`-Encoding UTF8` 会写入 BOM。需要 UTF-8 无 BOM 时使用：

```powershell
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText('.\example.txt', '你好，世界！', $utf8NoBom)
```

## 禁止误区

- 不要认为执行 `chcp 65001` 就能保证文件写入为 UTF-8；它主要影响控制台代码页，不会自动修正所有文件 API。
- 不要因为终端显示正常就跳过文件字节验证。
- 不要读取乱码后再覆盖原文件；错误解码可能造成不可逆的数据丢失。
- 不要在未知编码文件上直接做批量替换。

## 写后验证清单

- 使用严格 UTF-8 解码读取文件，失败即停止。
- 确认目标中文原文存在，且没有 `�`。
- 检查 `git diff` 或等价差异，确认未出现整文件乱码或异常 BOM。
- 对 JSON/YAML/源码继续运行解析器、编译器或相关测试。
- 若调用原生命令或批处理边界，避免让中文补丁正文经过依赖系统默认代码页的管道。
- UTF-8 解码成功只证明字节合法；还要检查引号、转义符等内容是否在命令参数边界被改变。

## 工具调用旁证

本次首次通过 Windows PowerShell 5.1 管道向 `apply_patch` 传递包含中文的补丁时，工具返回“需要 UTF-8 PATCH 参数”。随后直接传递多行补丁参数虽然解决了中文编码问题，但参数中的双引号又被原生命令参数处理改变。最终改用参数数组调用底层执行器，才同时保留 UTF-8 中文和双引号。这说明工具参数边界必须同时验证编码与参数保真度。
