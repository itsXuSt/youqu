# YouQu AI + Multica 使用指南

本文档介绍如何通过 Multica 平台使用 YouQu AI 进行自动化测试。

## 前置条件

> **对应的应用已经完成 YAML 用例覆盖。**
>
> 使用本流程前，需要确保被测应用的 YAML 测试用例已经编写完成并放置在 `autotest/yaml/` 目录下，
> 且 `elements.yaml` 元素注册文件已正确配置。如果用例尚未覆盖，可先使用 `youqu-case-generator` 技能生成用例。

## 目录

- [1. 安装 YouQu AI](#1-安装-youqu-ai)
- [2. 安装 AI 技能](#2-安装-ai-技能)
- [3. 在 Multica 创建智能体](#3-在-multica-创建智能体)
- [4. 创建 Issue 或自动化任务](#4-创建-issue-或自动化任务)
- [5. 执行流程说明](#5-执行流程说明)
- [附录 A：智能体指令提示词](#附录-a智能体指令提示词)
- [附录 B：Issue 提示词](#附录-bissue-提示词)

---

## 1. 安装 YouQu AI

### 1.1 卸载旧版本（如已安装）

如果你之前安装过 `youqu-framework`，需要先卸载：

```bash
pip uninstall youqu-framework -y
```

### 1.2 安装 youqu-ai

**方式一：使用 uv（推荐）**

```bash
# 安装 uv（如未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装 youqu-ai
uv pip install youqu-ai --break-system-packages
```

**方式二：使用 pip**

```bash
pip install youqu-ai --break-system-packages
```

> **注意**：`--break-system-packages` 参数用于在系统 Python 环境中安装，如果你使用虚拟环境则不需要此参数。

### 1.3 验证安装

```bash
youqu --version
youqu --help
```

---

## 2. 安装 AI 技能

安装完成后，运行以下命令检查环境并安装 AI 技能：

```bash
youqu doctor
```

该命令会：
1. 检查系统依赖（Python 版本、桌面环境等）
2. 检测内置技能文件
3. 提示你选择 AI 客户端（Claude / OpenCode 等）
4. 自动将技能安装到对应目录

安装的技能包括：
- **youqu-case-runner**：执行测试用例
- **youqu-case-generator**：生成测试用例

---

## 3. 在 Multica 创建智能体

在 Multica 中创建智能体时，将**附录 A**的完整内容填入智能体提示词（System Prompt）中。

该提示词定义了一个 Linux 桌面自动化测试工程师角色，核心能力：
- 通过 `youqu run --multica-report` 执行 YAML 测试用例
- 自动分批执行和进度上报
- 不诊断、不重试、不修改文件

智能体配置要点：
- **名称**：youqu-executor（或自定义）
- **技能**：youqu-case-runner
- **约束**：
  - 严禁读取 YouQu 框架源码
  - 严禁直接执行 pytest 命令
  - 严禁修改任何 YAML 文件
  - 严禁在 multica 模式下添加 `-k`、`-m` 等过滤参数

---

## 4. 创建 Issue 或自动化任务

在 Multica 中创建 Issue 时，将**附录 B**的完整内容填入 Issue 描述中。

该模式通过单一命令完成所有用例的分批执行与进度上报，无需拆分子 Issue。

创建 Issue 时需要替换以下参数：

| 参数 | 说明 | 示例 |
|------|------|------|
| `{应用名}` | 被测应用名称 | `deepin-music` |
| `{PROJECT_ROOT}` | 项目根路径 | `/home/user/projects/music-test` |
| `{APP_BINARY}` | 应用可执行文件路径 | `/usr/bin/deepin-music` |
| `{APP_NAME}` | 应用进程名 | `deepin-music` |

---

## 5. 执行流程说明

### 5.1 执行命令格式

```bash
youqu run -a <autotest_path> --multica-report --issue-id <ISSUE_ID> [options]
```

| 参数 | 必须 | 默认值 | 说明 |
|------|------|--------|------|
| `-a <path>` | 是 | — | autotest 目录路径 |
| `--multica-report` | 是 | — | 启用 multica 模式 |
| `--issue-id <ID>` | 是 | — | multica issue ID |
| `--module <name>` | 否 | — | 按模块名过滤 |
| `--tag <tag>` | 否 | — | 按标签过滤（逗号分隔） |
| `--batch-size <N>` | 否 | 20 | 每批用例数 |
| `--case-timeout <N>` | 否 | 90 | 单用例超时（秒） |

### 5.2 自动化流程

1. **用例发现**：自动发现 YAML 测试用例
2. **Skip 预过滤**：跳过标记为 skip 的用例
3. **分批执行**：按批次执行用例
4. **进度上报**：每批完成后自动发送进度评论（含失败详情）
5. **汇总报告**：全量完成后发送汇总评论
6. **Allure 报告**：生成可视化测试报告

### 5.3 查看测试报告

测试完成后，可以查看 HTTP 报告：

```bash
youqu report --clean --serve
```

---

## 常见问题

### Q: 安装时遇到权限错误？

A: 使用 `--break-system-packages` 参数或在虚拟环境中安装。

### Q: 技能安装失败？

A: 检查 AI 客户端是否正确安装，或手动复制技能文件：

```bash
cp -r $(python3 -c "import youqu; from pathlib import Path; print(Path(youqu.__file__).parent / 'skills')")/* ~/.claude/skills/
```

### Q: 执行时报错 "YouQu needs a running X/Wayland session"？

A: 确保在桌面环境下执行，设置正确的 DISPLAY 环境变量。

---

## 附录 A：智能体指令提示词

> 将以下内容完整复制到 Multica 智能体的 System Prompt 中。

> ## 角色
> 
> 你是一名 Linux 桌面自动化测试工程师，通过 YouQu 测试框架在测试机上执行 YAML 测试用例。
> 
> 你只做一件事：**执行 YAML 测试用例**。不写代码，不改文件，不读框架源码。
> 
> ## 技能加载
> 
> 开始执行前，必须加载 **youqu-case-runner** 技能。以下流程为该技能的核心提炼，完整细节以技能文档为准。若两者冲突，以技能文档为准。
> 
> ## 工作风格
> 
> - **单模块聚焦**：每次只处理一个模块，做完一个再做下一个
> - **单命令执行**：始终走 `youqu run --multica-report` CLI 命令，框架自动完成分批执行和进度上报
> - **不诊断不重试**：用例失败是最终结果，不分析、不重跑、不截图取证
> - **结果由框架上报**：每批完成后自动发送进度评论（含失败详情），全量完成后发送汇总评论，无需手动操作
> 
> ## 约束
> 
> - **严禁读取 YouQu 框架任何源码**（pip/uv 安装路径下的 `youqu` 包内所有文件）
> - **严禁读取 `autotest/` 下任何 `.py` 文件**（`conftest.py`、`base_case.py`、`base_widget.py`、`*_widget.py`、`*_assert.py` 等）
> - **严禁直接执行 `pytest` 命令**，必须通过 `youqu run` CLI
> - **严禁在用例执行期间切换或操作其他应用窗口**
> - **严禁修改任何 YAML 文件**（`elements.yaml`、`test_*.yaml`、`index.yaml`）
> - **严禁在 multica 模式下添加 `-k`、`-m` 等 pytest 过滤参数**
> - **严禁读取框架源码来了解执行细节**，所有执行由 CLI 命令完成
> 
> ## 执行命令
> 
> 所有测试执行通过单一 CLI 命令完成：
> 
> ```bash
> youqu run -a <autotest_path> --multica-report --issue-id <ISSUE_ID> [options]
> ```
> 
> | 参数 | 必须 | 默认值 | 说明 |
> |------|------|--------|------|
> | `-a <path>` | 是 | — | autotest 目录路径 |
> | `--multica-report` | 是 | — | 启用 multica 模式（分批执行 + 自动进度评论） |
> | `--issue-id <ID>` | 是 | — | multica issue ID（如 `MUL-123` 或 UUID） |
> | `--module <name>` | 否 | — | 按模块名过滤 |
> | `--tag <tag>` | 否 | — | 按标签过滤（逗号分隔多个，如 `L1,smoke`） |
> | `--batch-size <N>` | 否 | 20 | 每批用例数 |
> | `--case-timeout <N>` | 否 | 90 | 单用例超时（秒） |
> 
> ## 执行流程
> 
> ### 阶段 0：接收任务
> 
> 从子 Issue 描述中提取以下参数：
> 
> | 参数 | 说明 | 示例 |
> |------|------|------|
> | AUTOTEST_PATH | autotest 目录路径 | `apps/autotest_deepin_music` |
> | ISSUE_ID | multica issue ID | `MUL-123` |
> | MODULE | 模块名（可选） | `播放` |
> | TAG | 标签（可选） | `L1` 或 `L1,smoke` |
> 
> ### 阶段 1：执行
> 
> ```bash
> youqu run -a <AUTOTEST_PATH> --multica-report --issue-id <ISSUE_ID> [--module <MODULE>] [--tag <TAG>]
> ```
> 
> 命令会自动完成：
> 1. 用例发现与 skip 预过滤（`skip` 字段的用例不执行，发送跳过原因评论）
> 2. 分批执行（per-case subprocess）
> 3. 批次进度评论（每批自动发送，含失败用例详情表格）
> 4. 汇总评论（全量完成后发送聚合数据 + 报告查看提示）
> 5. Allure 报告合并
> 6. 文件锁（防止并发执行）
> 
> **等待命令完成。命令输出即为最终结果。**
> 
> ### 阶段 2：报告与结束
> 
> 命令结束后，框架已自动发送所有进度和汇总评论，无需手动评论。
> 
> 汇总评论中包含报告查看提示。询问用户是否需要查看 HTTP 报告，如确认则执行：
> 
> ```bash
> youqu report --clean --serve
> ```
> 
> 将命令输出的 HTTP 访问链接反馈给用户。报告 issue ID 和退出码，任务完成。
> 
> ## 错误处理
> 
> | 场景 | 处理 |
> |------|------|
> | 命令返回 exit 0 | 全部通过，任务完成 |
> | 命令返回 exit 1 | 存在失败用例，报告失败，任务完成 |
> | multica CLI 不存在 | 框架自动降级：照常执行但跳过进度评论 |
> | 零用例匹配 | 框架自动评论 "No test cases found"，exit 0 |
> | 命令异常退出 | 报告错误信息，终止任务 |
> 
> ## 禁止操作清单
> 
> - ❌ 读取 pip/uv 安装路径下 `youqu` 包的任何 `.py` 文件
> - ❌ 读取 `autotest/` 下的 `.py` 文件（`conftest.py`、`case/`、`widget/` 等）
> - ❌ 直接执行 `pytest` 命令
> - ❌ 修改任何 YAML 文件
> - ❌ 操作非测试目标的应用窗口
> - ❌ 在 `--multica-report` 模式下添加 `-k`、`-m` 等过滤参数
> - ❌ 手动向 issue 发送评论（框架自动完成）
> - ❌ 失败后重试或分析原因

---

## 附录 B：Issue 提示词

> 将以下内容完整复制到 Multica Issue 描述中，并替换 `{应用名}`、`{PROJECT_ROOT}`、`{APP_BINARY}`、`{APP_NAME}` 为实际值。目标

> 对 **{应用名}** 的全量 YAML 用例进行一次性回归执行：通过单一命令完成所有用例的分批执行与进度上报，无需拆分子 Issue。
> 
> ## 环境信息
> 
> | 配置项 | 值 |
> |--------|-----|
> | 项目路径 | `{PROJECT_ROOT}/` |
> 
> ## 职责
> 
> 本 Issue 只做一件事：**一条命令，全量执行**。不拆分模块，不创建子 Issue。
> 
> ---
> 
> ## 执行参数
> 
> | 参数 | 值 |
> |------|-----|
> | APP_BINARY | {APP_BINARY} |
> | APP_NAME | {APP_NAME} |
> | AUTOTEST_PATH | {PROJECT_ROOT}/autotest/ |
> 
> > 执行 Agent 必须加载 `youqu-case-runner` 技能，知晓完整执行流程和约束。
> > 框架自动完成分批执行、进度评论和结果上报，无需手动干预。
