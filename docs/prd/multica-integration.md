# PRD: YouQu × multica 异步测试执行集成

**版本**: v0.3
**日期**: 2026-06-12
**状态**: 草稿 (审查修正)

---

## 1. 问题陈述

### 1.1 现状

multica 平台通过 issue 驱动 AI 智能体 (OpenCode/Claude Code) 在测试机上执行 YouQu YAML 测试。当前流程：

```
multica issue 分配给智能体 → daemon 拉取任务 → 启动 AI 工具
→ AI 工具: 探索项目 → shell 命令 → 读输出 → 思考 → 下一命令 → ... → 超时
```

**耗时是本地 CLI 直接执行的 3-5 倍**。根因：
- AI 智能体的迭代 shell 调用模式：每步触发 LLM 推理 (10-60s) + shell 往返
- 错误后反复重试
- 空闲看门狗 (30min) 或工具看门狗 (2h) 超时导致任务失败

### 1.2 目标

1. **智能体单命令执行**：1 条 `youqu run` CLI 命令，零探索、零重试、零分析
2. **CLI 分批执行 + 增量进度回报**：每批测试完成后向 multica issue 推送进度评论，保持看门狗存活
3. **串行保证**：测试运行时禁止其他进程操作 GUI
4. **multica 平台透传**：issue 格式 → CLI 参数自动映射

---

## 2. 架构概览

```
┌──────────────────────────────────────────────────────────────────────┐
│                        multica (Cloud/Self-Host)                     │
│                                                                      │
│  Issue 创建                                                          │
│    │                                                                 │
│    ▼                                                                 │
│  分配给 youqu-runner 智能体                                          │
│    │                                                                 │
│    ▼ (WebSocket 派发)                                                 │
│  Daemon (测试机)                                                      │
│    │                                                                 │
│    ▼ (启动 OpenCode/Claude，注入 Skill + 系统指令)                     │
│  AI 工具                                                             │
│    │                                                                 │
│    ▼ (单次 shell 调用)                                                │
│  youqu run --multica-report --issue-id MUL-123 --batch-size 20       │
│    │                                                                 │
│    ├── idx.query(module="播放") → 205 tests, 11 batches              │
│    │   multica issue comment add "🔍 Resolved 205 cases..."          │
│    │                                                                 │
│    ├── Batch 1/11 (each case as subprocess):                          │
│    │     subprocess.run(pytest case_001, timeout=90, --alluredir ...) │
│    │     → 18p/2f/0s                                                  │
│    │   multica issue comment add "📊 Batch 1/11: 18p/2f/0s (90%)"   │
│    │                                                                 │
│    ├── ... (stdout 每 10 条心跳 → watchdog 不触发)                    │
│    │                                                                 │
│    ├── _merge_allure_dirs() → unified report/allure_raw/              │
│    └── multica issue comment add "✅ Done: 185/205 (90.2%)"           │
│        exit 0                                                        │
│                                                                      │
│  Daemon 上报 completed → issue 状态可自动流转                        │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.1 主 issue vs 子 issue 模式

测试范围由 multica issue 层级决定，不在 CLI 层面做关键词筛选：

| 模式 | issue 类型 | CLI 命令 | 典型场景 |
|------|-----------|----------|----------|
| 全量 | 主 issue | `youqu run --multica-report` | 每日回归、版本发布前全量 |
| 模块 | 子 issue | `... --module 播放` | 播放模块变更后的定向测试 |
| 标签 | 子 issue | `... --tag L1` | 冒烟测试、快速验证 |

**设计理由**: `-k` (pytest keyword) 是面向人工交互的临时筛选手段。在 multica 驱动的自动化流程中，测试选择应通过 issue 结构表达——创建 issue 的人决定跑什么，智能体只负责执行。这避免了智能体"猜测"筛选条件的不确定性。

### 2.2 为何不触发 multica 超时

| 超时类型 | 阈值 | 如何避免 |
|----------|------|----------|
| 服务端硬上限 | 2.5h | 单次执行远低于此 |
| 空闲看门狗 (idle watchdog) | 30min | pytest subprocess 持续输出 stdout |
| 工具看门狗 (tool watchdog) | 2h | 同上 |
| 每批后发进度评论 | — | 复证 AI 工具仍在活动 |

---

## 3. 环境检测与前置条件

### 3.1 multica 环境识别

**方案 A (推荐)**: `--multica-report` 标志显式激活。不依赖环境变量自动检测，避免误触发。

**方案 B (备选)**: 检测 `MULTICA_ISSUE_ID` 环境变量。multica daemon 在启动 AI 工具时会注入任务相关环境变量。需验证 daemon 是否注入 issue ID。

**决策**: 采用方案 A。显式标志无歧义，不依赖 daemon 行为。

### 3.2 multica CLI 可用性检测

`youqu run --multica-report` 执行时：

```python
def _check_multica_cli():
    """Check if multica CLI is available and authenticated."""
    import shutil
    if shutil.which("multica") is None:
        print("Warning: multica CLI not found. Progress will not be posted.")
        return False
    # 验证 PAT 存在
    config_path = Path.home() / ".multica" / "config.json"
    if not config_path.exists():
        print("Warning: multica not authenticated. Run 'multica login' first.")
        return False
    return True
```

**降级策略**：multica CLI 不可用时，仍正常执行测试，仅跳过进度推送。不影响本地直接 `youqu run` 使用。

### 3.3 涉及的 multica 组件

| 组件 | 用途 | 是否需要改动 |
|------|------|:----------:|
| `multica` CLI | `youqu` 调用它发评论 | ❌ |
| PAT 令牌 | CLI 认证 (`.multica/config.json`) | ❌ |
| 智能体定义 | 系统指令 + Skill 挂载 | ✅ 新建 |
| Skill | 智能体行为约束 | ✅ 新建 |
| Issue 模板 | 标准化测试请求格式 | ✅ 新建 |
| Daemon | 任务派发和执行 | ❌ |

---

## 4. youqu CLI 改动

### 4.1 新增参数

```
youqu run \
  --multica-report              # 激活 multica 集成模式
  --issue-id MUL-123           # multica issue ID (必需)
  --batch-size 20              # 每批用例数 (默认 20)
  --case-timeout 90            # 单条用例超时秒数 (默认 90)
  --module 播放                 # 按模块筛选 (可选，透传 YamlIndex.query)
  --tag L1,smoke               # 按标签筛选 (可选，逗号分隔)
```

**不含 `-k`**: `-k` 是 pytest 关键词筛选，面向人工交互。multica 模式下测试选择由 issue 层级决定。

**默认行为**: 无 `--module` 和 `--tag` 时，执行 `ALL`（全部用例）。

### 4.1.1 `--case-timeout` 设计理由

桌面 UI 自动化中，AT-SPI 元素查找失败时可能陷入死循环或阻塞：

| 阻塞场景 | 触发条件 | 后果 |
|----------|---------|------|
| `wait_for` 超时过长 | YAML 中 `timeout: 60000` (60s) | 单个步骤等 60s 才失败 |
| `dog.click()` 无限重试 | 元素不可点击，dogtail 内部重试 | 单条用例永久阻塞 |
| 应用崩溃后 AT-SPI 树异常 | 进程已退出但 AT-SPI 注册未清理 | 所有后续查找挂死 |
| DBus 调用超时 | 服务无响应 | 单步阻塞 25s (默认 DBus 超时) |

**对策**: 每条用例独立子进程执行，超时后 `SIGTERM` 杀死，标记为 `timeout` 失败，继续下一条。每个用例写入独立 Allure 目录防止覆盖。

```
Batch 3/11:
  ├── subprocess.run(pytest test_play_041.yaml,
  │     --alluredir batch_3/case_041, timeout=90)  → pass
  ├── subprocess.run(pytest test_play_042.yaml,
  │     --alluredir batch_3/case_042, timeout=90)  → pass
  ├── subprocess.run(pytest test_play_043.yaml,
  │     --alluredir batch_3/case_043, timeout=90)  → TIMEOUT (SIGTERM)
  ├── subprocess.run(pytest test_play_044.yaml,
  │     --alluredir batch_3/case_044, timeout=90)  → pass
  └── ...
```

**Allure 数据合并**: 所有批次完成后，将 `report/batch_*/case_*/` 下的 allure 原始数据拷贝到统一 `report/allure_raw/` 目录，再生成 HTML 报告。避免逐用例子进程覆盖问题。

**与当前 `execute_batches()` 的区别**: 当前是单次 `pytest file1.yaml file2.yaml ...` 子进程整批写一个 `--alluredir`，改版后逐用例独立目录 + 最后合并。

### 4.2 执行流程

```
run(autotest_path, extra, multica_report, issue_id, batch_size, case_timeout, module, tag)
  │
  ├── 1. _find_autotest_dir() — 定位 autotest/
  │
  ├── 2. _acquire_test_lock() — 获取文件锁 (无论哪种模式都检查)
  │
  ├── 3. 若 multica_report:
  │       ├── _check_multica_cli() — 检测 multica 可用性
  │       ├── YamlIndex(autotest/yaml).query(module=module, tags=tag_list) — 解析用例列表
  │       │     ├── 有 module → 按模块筛选
  │       │     ├── 有 tag    → 按标签筛选
  │       │     └── 均无     → 执行 ALL
  │       ├── _post_multica_comment(issue_id, "🔍 Resolved N cases, M batches")
  │       │
  │       ├── run_batches(ids, file_map, batch_size, case_timeout, per_batch_callback=...)
  │       │     └── for case in batch:
  │       │           subprocess.run(pytest on single YAML file, timeout=case_timeout,
  │       │                          --alluredir batch_N/case_XXX)
  │       │           _parse_pytest_output(stdout) → pass/fail/timeout
  │       │           per_case_callback(case_result) → 累计统计
  │       │         _post_multica_comment(issue_id, batch_progress_markdown)
  │       │
  │       ├── _merge_allure_dirs() — 合并所有用例 allure 数据到统一目录
  │       └── _post_multica_comment(issue_id, final_summary)
  │
  └── 4. 否则 (非 multica 模式):
          └── 现有逻辑: pytest.main(pytest_args)
```

### 4.3 文件改动清单

| 文件 | 改动 | 说明 |
|------|------|------|
| `cli/main.py` | 加 argparse 参数 | `--multica-report`, `--issue-id`, `--batch-size`, `--case-timeout`, `--module`, `--tag` |
| `cli/run.py` | 重构 `run()` | 集成 batch 路径，调用 `multica_report` 模块 |
| `cli/multica_report.py` | **新文件** | multica 集成核心：进度评论、结果格式化、CLI 检测 |
| `src/mcp/jobs.py` | 可能复用 | `execute_batches()` / `_parse_pytest_output()` 逻辑提取到共享模块 |

### 4.4 复用与改造

当前 `execute_batches()` (`src/mcp/jobs.py`) 采用"整批单子进程"模式：

```python
# 当前: pytest file1.yaml file2.yaml ... → 一个 subprocess，timeout=600
cmd = [sys.executable, "-m", "pytest", ...] + file_paths
subprocess.run(cmd, timeout=600)
```

**缺陷**: 一个用例挂死，整批阻塞 600s。

**改造**: 提取纯批处理逻辑为 `src/yaml_test/batch_runner.py`，改为"逐用例子进程"模式：

```python
from src.yaml_test.batch_runner import run_batches

result = run_batches(
    test_ids=ids,
    yaml_dir=yaml_dir,
    pytest_ini_dir=autotest,
    batch_size=batch_size,
    case_timeout=90,                         # 每条用例 90s 超时
    per_batch_callback=_post_progress,       # 每批完成后回调
    per_case_callback=_accumulate_stats,     # 每条用例完成后累计
)

# 内部实现:
# for case in batch:
#     proc = subprocess.run(
#         [sys.executable, "-m", "pytest", ..., case_file],
#         timeout=case_timeout,
#     )
#     if proc.returncode == 0: passed += 1
#     elif isinstance(proc, TimeoutExpired): timeout += 1
#     else: failed += 1
```

**与 MCP 兼容**: `execute_batches()` 保持现有接口不变 (MCP 的 `yaml_run_batch` 调用它)，`run_batches()` 为新增公共函数。

---

## 5. multica 进度评论格式

### 5.1 进度评论 Markdown 模板

**初始评论**:
```markdown
🚀 **YouQu Test Started**
- App: `deepin-music`
- Module: `播放`
- Cases: 205 | Batches: 11 (batch size: 20)
- Started: 2026-06-12 14:30:00
```

**每批进度评论**:
```markdown
📊 **Progress: Batch 5/11**
- Batch: test_play_081..test_play_100
- Passed: 17 | Failed: 2 | Timeout: 1 | Skipped: 0
- Pass Rate: 85%
- Time: 3m 12s
```

**最终摘要评论**:
```markdown
✅ **YouQu Test Complete**
- Total: 205 | Passed: 185 | Failed: 17 | Timeout: 1 | Skipped: 2
- Pass Rate: 90.2%
- Duration: 28m 15s
- Allure: `autotest/report/allure_html/` (local path)
```

### 5.2 评论频率控制

| 参数 | 值 | 说明 |
|------|-----|------|
| 每批发评论 | 1 条 | 批完成后立即推送，不按用例拆 |
| 评论字符上限 | 4000 | multica 无硬限制，但留余量 |

**最坏情况防护**: 若某批全部超时 (batch_size × case_timeout → 20 × 90s = 30min)，最后一次进度评论距下一次可能刚好触碰 30min idle watchdog 边界。防护措施：
- 批次内部每执行 10 条用例向 stdout 输出一行心跳日志 `[youqu] case 10/20 done`
- daemon 通过 AI 工具 stdout 感知活动，不会仅依赖评论间隔

---

## 6. multica 智能体与 Skill

### 6.1 智能体定义

```
名称: youqu-runner
AI 工具: OpenCode (推荐) / Claude Code
可见性: workspace (或 private)
并发上限: max_concurrent_tasks = 1
```

**系统指令 (instructions)**:
```
你是 YouQu 测试执行智能体。唯一职责：执行 youqu CLI 运行自动化测试。

## 核心规则
1. **禁止探索** - 不读文件、不搜索代码、不分析项目结构
2. **禁止重试** - 测试失败不重跑、不调试、不分析原因
3. **单命令执行** - 只发一条 shell 命令，不做额外操作
4. **禁止自行筛选** - 不使用 -k/-m 等 pytest 筛选参数，测试范围由 issue 描述决定
5. **立即退出** - 命令执行完就结束

## 执行流程
收到 issue 后：
1. 从 issue 标题/描述中提取：app_path、module、tag
2. 获取 issue ID：
   - multica 环境变量 `MULTICA_ISSUE_KEY` (格式 MUL-123) 或 `MULTICA_ISSUE_ID` (UUID)
   - 如果环境变量不可用，从当前 issue 上下文中提取 issue key
3. 运行:
   - 主 issue (全量): youqu run -a <app_path> --multica-report --issue-id <key>
   - 子 issue (模块): ... --issue-id <key> --module <m>
   - 子 issue (标签): ... --issue-id <key> --tag <t>
4. 结束
```

### 6.2 Skill 定义

Skill 文件放置于 youqu 项目 `skills/youqu-multica-runner/SKILL.md`，在 multica 平台挂载给智能体。与 `youqu-case-runner` 平级。

```yaml
---
name: youqu-multica-runner
version: "0.1.0"
description: >
  YouQu multica test executor. Constrains agent to single CLI command with
  batched execution and incremental progress reporting. No exploration,
  no retry, no analysis.
---
```

**关键约束** (与普通 `youqu-case-runner` 的区别):
- 无 `yaml_list_tests` MCP 调用 (索引/筛选由 CLI 内部完成)
- 无 `yaml_get_status` 轮询 (进度由 CLI 主动推送)
- 无失败诊断 (CLI 自行收集结果)
- 单命令退出，不等待

### 6.3 Skill 分发与更新

| 方式 | 说明 |
|------|------|
| 初始安装 | `youqu doctor` 自动复制到 `~/.config/opencode/skills/` |
| multica 导入 | `multica skill import --url https://github.com/linuxdeepin/youqu/raw/...` |
| 版本管理 | `SKILL.md` 头部的 `version` 字段，与 youqu 版本号解耦 |
| 更新触发 | youqu 发布新版本时附带更新 Skill |

---

## 7. Issue 提示词格式 (标准化模板)

multica 上测试选择由 **issue 层级** 决定，而非 CLI 参数：

```
主 issue (全部测试)
  │
  ├── 子 issue 1: 模块 A (--module A)
  ├── 子 issue 2: 模块 B (--module B)
  └── 子 issue 3: L1 标签 (--tag L1)
```

### 7.1 主 issue 模板 (全量测试)

```markdown
## 测试任务: deepin-music 全量回归

**应用**: deepin-music
**类型**: 全量测试

## 执行参数
- app_path: apps/autotest_deepin_music
- batch_size: 20

## 期望
- 执行全部 YAML 用例
- 分批执行，每批 20 个
- 结果自动回帖到本 issue
```

**智能体提取**: `app_path` → `youqu run -a apps/autotest_deepin_music --multica-report --issue-id $ISSUE_ID`

### 7.2 子 issue 模板 (按模块/标签)

```markdown
## 测试任务: deepin-music 播放模块

**应用**: deepin-music
**模块**: 播放
**类型**: 模块测试

## 执行参数
- app_path: apps/autotest_deepin_music
- module: 播放
- batch_size: 20
```

**智能体提取**: `youqu run -a apps/autotest_deepin_music --multica-report --issue-id $ISSUE_ID --module 播放`

### 7.3 子 issue 模板 (按标签)

```markdown
## 测试任务: deepin-music L1 冒烟

**应用**: deepin-music
**标签**: L1
**类型**: 标签筛选

## 执行参数
- app_path: apps/autotest_deepin_music
- tag: L1
- batch_size: 20
```

**智能体提取**: `youqu run -a apps/autotest_deepin_music --multica-report --issue-id $ISSUE_ID --tag L1`

### 7.4 参数提取规则

智能体从 issue 描述中提取结构化参数，组装 CLI 命令：

```
app_path → -a <app_path>
module   → --module <module>
tag      → --tag <tag>
均无     → 无 --module/--tag (执行全部)
```

**明确禁止**: 智能体不得自行添加 `-k`、`-m` 等 pytest 原生筛选参数。测试范围由 issue 描述决定。

---

## 8. 串行保证

### 8.1 multica 层面

`max_concurrent_tasks = 1` — 同一智能体不同时执行两个任务。

### 8.2 文件锁 (安全网)

```python
import fcntl

_LOCK_FILE = "/tmp/youqu-test.lock"

def _acquire_test_lock():
    """Acquire exclusive lock to prevent concurrent test execution."""
    lock_fd = open(_LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_fd
    except BlockingIOError:
        print("Error: Another youqu test is already running. Exiting.")
        sys.exit(1)
```

**设计理由**:
- 锁在 `run()` 入口获取，覆盖 multica 模式和本地 `youqu run` 模式
- 防止 multica 平台配置错误导致同机两个不同智能体同时执行
- 防止用户手动 `youqu run` 与 multica 自动执行冲突
- 进程退出时内核自动释放锁 (`fcntl.flock` 特性)

### 8.3 锁的生命周期

| 阶段 | 动作 |
|------|------|
| `youqu run --multica-report` 启动 | 获取锁 |
| 运行中 | 锁被持有 |
| 正常退出 / `sys.exit()` | 锁自动释放 |
| 进程被 kill -9 | 内核释放锁 |
| 进程崩溃 (SIGSEGV) | 内核释放锁 |

---

## 9. 错误处理与降级

### 9.1 错误矩阵

| 场景 | youqu 行为 | issue 表现 |
|------|-----------|------------|
| multica CLI 未安装 | 执行测试，跳过进度推送 | 无进度评论，但测试正常运行 |
| multica 未认证 (PAT 过期) | 同上 | 同上 |
| `multica issue comment` 失败 | 打印 stderr，继续下一批 | 缺失部分批次进度评论 |
| **单条用例超时 (90s)** | **SIGTERM 杀子进程，标记 timeout，继续下一条** | **进度评论显示 timeout 计数** |
| 文件锁已被持有 | 立即退出，exit 1 | 智能体上报 failed + 错误信息 |
| YamlIndex 不存在 | 退出，exit 1 | 同上 |
| `--issue-id` 缺失 | 退出，exit 1 | 同上 |

### 9.2 部分成功处理

即使部分批次失败，`youqu run` 仍返回非零退出码，但：
- 进度评论包含所有已完成批次的结果
- 最终摘要评论包含完整统计

```markdown
⚠️ **YouQu Test Complete (partial)**
- Total: 205 | Passed: 165 | Failed: 35 | Timeout: 3 | Skipped: 2
- Pass Rate: 80.5%
- Duration: 32m 10s
```

---

## 10. 取消机制

### 10.1 multica 任务取消

用户通过 multica UI 取消任务时：
1. Daemon 向 AI 工具进程发送 SIGTERM
2. AI 工具进程终止 → youqu 子进程收到 SIGTERM
3. youqu 在批次间检查取消信号 → 优雅退出

### 10.2 优雅退出

```python
import signal

_cancelled = False

def _on_sigterm(signum, frame):
    global _cancelled
    _cancelled = True

signal.signal(signal.SIGTERM, _on_sigterm)

# 在批次循环中检查
for batch in batches:
    if _cancelled:
        _post_multica_comment(issue_id, "⏹️ Cancelled by user. Completed 5/11 batches.")
        sys.exit(1)
    # ... 执行批次 ...
```

---

## 11. 向后兼容

### 11.1 不变的路径

| 场景 | 命令 | 行为 |
|------|------|------|
| 本地直接执行 | `youqu run` | **不变** — 走原有 `pytest.main()` 路径 |
| 本地 + 过滤 | `youqu run -k "xxx"` | **不变** |
| multica 模式 | `youqu run --multica-report --issue-id MUL-123` | **新路径** — 分批 + 进度评论 |

### 11.2 不影响的功能

- `youqu run` 原有行为 100% 保留
- `youqu manage.py run` 不受影响
- `conftest.py` 报告生成 (Allure/JSON) 不受影响
- MCP `yaml_run_batch` 不受影响
- `pytest.ini` 配置不需要任何修改

---

## 12. 实施计划

### 12.1 Phase 1: CLI 核心 (2-3 天)

| 任务 | 文件 | 产出 |
|------|------|------|
| 提取 batch runner (逐用例模式) | `src/yaml_test/batch_runner.py` (新) | `run_batches()` 公共函数，`case_timeout` 支持 |
| multica 集成模块 | `cli/multica_report.py` (新) | 进度评论、CLI 检测、结果格式化 |
| CLI 参数扩展 | `cli/main.py` | 6 个新参数 (`--multica-report`, `--issue-id`, `--batch-size`, `--case-timeout`, `--module`, `--tag`) |
| CLI 执行路径 | `cli/run.py` | `--multica-report` 条件分支 |
| jobs.py 适配 | `src/mcp/jobs.py` | `execute_batches()` 保持向后兼容 |

### 12.2 Phase 2: Skill 与配置 (1 天)

| 任务 | 文件 | 产出 |
|------|------|------|
| multica Skill | `skills/youqu-multica-runner/SKILL.md` (新) | 智能体约束 Skill |
| Skill 安装 | `cli/doctor.py` | doctor 自动安装到 opencode/claude 目录 |
| Issue 模板 | 文档 | 标准化 issue 模板 |

### 12.3 Phase 3: 验证 (1-2 天)

| 任务 | 说明 |
|------|------|
| 单元测试 | `tests/test_multica_report.py` — mock multica CLI |
| 本地模拟 | `youqu run --multica-report --issue-id TEST-001 --batch-size 5` |
| multica 集成测试 | 真实 multica 环境端到端验证 |
| 串行测试 | 验证文件锁，并发启动两个 youqu run |

---

## 13. 开放问题

| # | 问题 | 状态 |
|---|------|------|
| 1 | multica daemon 是否注入 `MULTICA_ISSUE_KEY` / `MULTICA_ISSUE_ID` 环境变量？ | 待验证 |
| 2 | `multica issue comment add` 的 `--content` 字符上限？ | 待验证（保守设 4000） |
| 3 | `--case-timeout` 默认 90s 是否合理？需根据实际用例耗时分布调优 | 待实测 |
| 4 | `subprocess.run` 逐用例调用的启动开销 (pytest + youqu import) 是否可接受？ | 待实测（预估 2-3s/case） |
| 5 | 智能体系统指令是否可在 multica 平台直接配置而不依赖 Skill？ | 已确认：支持 instructions 字段 |
| 6 | 多个 APP 工程的 autotest/ 目录共存时，`-a` 参数如何指定？ | 已有 `--app` 参数
| 7 | 非 YAML 用例 (Python PO 模式) 是否纳入 multica 集成范围？ | **暂不纳入** — v0.1 仅 YAML |

---

## 14. 附录

### A. multica CLI 命令参考

```bash
# 发评论
multica issue comment add <issue-id> --content "markdown content"

# 更新 issue 状态
multica issue status <issue-id> done

# 列出评论
multica issue comment list <issue-id>
```

### B. 相关文件路径

```
youqu/
├── cli/
│   ├── main.py              # CLI 参数定义
│   ├── run.py               # 执行入口 (待改动)
│   └── multica_report.py    # 【新】multica 集成 (进度评论、CLI检测)
├── src/
│   ├── yaml_test/
│   │   ├── index.py         # YamlIndex — 用例索引/筛选
│   │   └── batch_runner.py  # 【新】批处理执行器
│   └── mcp/
│       └── jobs.py          # execute_batches (待适配)
├── skills/
│   └── youqu-multica-runner/
│       └── SKILL.md         # 【新】multica 智能体 Skill
└── docs/
    └── prd/
        └── multica-integration.md  # 本文档
```

### C. multica 架构速览

```
Multica Server (Go + PostgreSQL)
    │
    ├── WebSocket ← 实时推送 (事件通知, 非内容流)
    │
    └── REST API ← 评论 CRUD
         ├── POST /api/issues/{id}/comments   创建评论
         ├── PUT  /api/comments/{id}          更新评论 (CLI 未暴露)
         └── GET  /api/issues/{id}/comments   读取评论

Daemon (测试机)
    ├── 3s 轮询任务
    ├── 15s 心跳
    ├── 启动 AI 工具 (OpenCode/Claude)
    └── 流式上报工具输出到 Server
```
