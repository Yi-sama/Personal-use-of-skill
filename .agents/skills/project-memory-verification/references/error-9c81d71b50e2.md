# 案例 005：OpenCV 复核受 Python 环境差异影响

CASE-HASH: 9c81d71b50e2

## 问题描述

一次 OpenCV 复核因为当前 Python 环境无法导入 `cv2` 而没有执行。这个现象不能直接推出“机器没有 OpenCV”；不同 Python、Conda 环境可能各自拥有不同依赖集合。

## 当前环境实测

默认 `python` 指向 `D:\Miniconda3\python.exe`，导入 `cv2` 失败；`C:\Python313\python.exe` 和 `C:\Python314\python.exe` 也没有 `cv2`。

已存在的 Conda 环境中：

| 环境 | `cv2` 状态 | 版本 |
| --- | --- | --- |
| `base` | 不可导入 | - |
| `ancoda_getspark` | 可导入 | 4.11.0 |
| `blender_rag` | 不可导入 | - |
| `moneyprinterturbo` | 不可导入 | - |
| `talestreamai` | 不可导入 | - |
| `yolo` | 可导入 | 4.13.0 |

在 `ancoda_getspark` 和 `yolo` 中，内存图像 PNG 编码、解码和尺寸断言均通过 `OPENCV_SMOKE=PASS`。

## 根因

复核命令使用了不含 `cv2` 的解释器，而不是项目实际依赖所在的 Python 环境。根因是环境选择没有作为复核前置条件记录和确认；不是 OpenCV API 本身失败。

## 默认规则：不需要复验

这类环境探测和 OpenCV smoke test 不属于每次任务的必执行步骤。除非当前任务确实涉及图像处理、视频处理或 OpenCV 相关代码，否则：

1. 不安装 `opencv-python` 或切换 Conda 环境。
2. 不为了“补齐验证”重复运行 OpenCV 复核。
3. 仅在报告中说明“当前解释器缺少 `cv2`，该项复核未执行”。
4. 不把“未执行”写成“项目功能失败”。

## 需要 OpenCV 时的可选核验

只有任务确实需要 OpenCV 时，先确认项目指定的解释器，再运行最小导入检查：

```powershell
conda run -n <project-env> python -c "import cv2,sys; print(sys.executable); print(cv2.__version__)"
```

如果需要确认核心 API，再执行内存图像编码/解码 smoke test。没有明确项目环境时，停止在环境诊断，不自行安装依赖或改变环境。

## 结论

“当前环境缺少 `cv2`”是有效的局部事实；“机器没有 OpenCV”是未经证实的扩大结论。此次复验已经在两个已有环境中完成，后续普通任务无需重复执行。
