# PRD: YAML 用例索引 + MCP 异步批量执行

**版本**: v1.0
**日期**: 2026-06-09
**状态**: 待审查

---

## 1. 问题陈述

### 1.1 痛点一: YAML 用例无索引、无分类、不可查询

当前 `TestCase` Pydantic 模型仅有 `name`(标题)和 `app`(应用名)两个业务字段。所有 YAML 文件平铺在 `yaml/` 目录下，无模块/功能分类。

**对 AI 的影响**:
- AI 执行 `ls autotest/yaml/*.yaml` 获取文件名列表，不知道用例测什么
- 无法回答"music 的播放模块有哪些用例"
- `youqu run -k "播放"` 依赖中文关键词匹配文件名或用例名，不可靠
- 用户说"只测播放功能"，AI 只能运行全部用例

**对比 Python 用例**: Python 用例通过 CSV 文件管理标签(L1/L2/smoke/skip/fixed)，YAML 无对应机制。

### 1.2 痛点二: YAML 用例缺少原始测试步骤/期望，无法校对和验收

YAML 用例生成后仅有自动化步骤(action/assert)，缺少原始测试用例的步骤描述和预期结果。

**影响**:
- 评审者打开 YAML 文件无法对照原始需求验收
- 不确定自动化步骤是否完整覆盖了原始用例的所有验证点
- 从 xlsx/csv 生成的 YAML 丢失了原始"测试步骤"和"预期结果"两列信息

**期望**: 每个 YAML 文件头部包含 `description` 字段，记录原始用例的步骤和期望，作为 YAML 校对和验收的参考依据。

### 1.3 痛点三: `youqu run` 阻塞执行，AI 无法监控进度

```
AI 调用 → youqu run → pytest.main() → 阻塞 N 分钟 → 一次性返回全部输出
```

**根因**: MCP 客户端(OpenCode/Claude)的工具调用超时 ~30-120s。15 个 YAML 用例 × 平均 10s/个 = 150s，必然超时。

**后果**:
- 工具调用被 kill，AI 收不到结果
- AI 不知道哪些用例通过、哪些失败
- 任务失败，无恢复手段

**对比 deepin-mcp**: deepin-mcp 使用 JobManager + `get_job_status` 轮询，AI 可在 30s 超时内获得进度，然后继续轮询。

---

## 2. 目标与非目标

### 2.1 目标 (MUST)

| # | 目标 | 验证方式 |
|---|------|---------|
| G1 | YAML 用例支持 `module`/`feature`/`tags` 元数据 | 新生成 YAML 包含这些字段，旧 YAML 解析不报错 |
| G2 | 自动生成 `yaml/index.yaml` 索引文件 | `youqu make` 后索引文件存在且内容正确 |
| G3 | MCP 工具 `yaml_list_tests` 可查询用例 | 按 module/feature/tags 过滤返回用例列表 |
| G4 | MCP 工具 `yaml_run_batch` 提交异步批量执行 | 返回 `job_id`，AI 可在 30s 内获得响应 |
| G5 | MCP 工具 `yaml_get_status` 轮询执行进度 | 返回当前 batch 号、完成数、通过/失败/跳过 |
| G6 | MCP 工具 `yaml_cancel` 可取消运行中任务 | 已完成的 batch 结果保留，未开始的取消 |
| G7 | 批量执行每批 ≤ 5 个用例，批次间串行 | 日志显示 batch N/M 进度 |
| G8 | 向后兼容 — 旧 YAML(无 module/feature/tags)正常工作 | 旧用例照常执行，归类为 `module=uncategorized` |
| G9 | YAML 用例支持 `description` 字段记录原始测试步骤和期望 | 生成/解析 YAML 时 `description` 正确保存和读取 |

### 2.2 非目标 (NOT)

| # | 非目标 | 原因 |
|---|--------|------|
| N1 | 实时 SSE 进度推送 | 轮询足够(deepin-mcp 证实可用)，SSE 增加复杂度 |
| N2 | 多 batch 并发执行 | UI 自动化必须串行(单桌面、单 AT-SPI 连接) |
| N3 | 修改 pytest collection 逻辑 | 在 MCP 层切分 batch，不侵入框架核心 |
| N4 | 与 CSV 标签系统统一 | YAML 和 Python 用例标签体系独立，统一是后续 PRD |
| N5 | 支持 Python 用例的异步执行 | 首期仅 YAML(AI 主要操作对象)，Python 后续扩展 |
| N6 | `manage.py remote` 集成 | 远程执行是独立功能，不在本期范围 |
| N7 | 测试执行失败自动重试 | 复用 pytest `--reruns` 参数，不在 MCP 层做 |

---

## 3. 用户故事

### US1: AI 查询可用用例
> **作为** AI 测试助手
> **我想** 查询"音乐播放"模块有哪些 YAML 测试用例
> **以便** 告诉用户可用的测试范围，并选择要执行的用例子集

```python
# MCP 调用
yaml_list_tests(app="deepin-music", feature="播放")

# 返回
{
  "tests": [
    {"id": "test_music_play_001", "name": "音乐-播放本地MP3", "module": "播放", ...},
    {"id": "test_music_play_002", "name": "音乐-播放在线流", "module": "播放", ...}
  ],
  "total": 2
}
```

### US2: AI 异步批量执行
> **作为** AI 测试助手
> **我想** 提交一批 YAML 用例异步执行，并查询进度
> **以便** 在 MCP 工具超时前获得响应，持续轮询直到完成

```python
# 提交
resp = yaml_run_batch(test_ids=["test_music_play_001", ...])  # 返回 job_id

# 轮询
while True:
    status = yaml_get_status(job_id)
    # status.progress = "batch 2/4: running test_music_play_006 (3/5 in batch)"
    if status.is_terminal:
        break
```

### US3: 用例生成时自动建立索引
> **作为** youqu-case-generator 技能
> **我想** 生成 YAML 用例时自动包含 module/feature/tags 并更新索引
> **以便** 新生成的用例立即可被查询和执行

---

## 4. 架构设计

### 4.1 整体数据流

```
┌──────────────────────────────────────────────────────────────────┐
│                        AI Client (OpenCode)                      │
│                                                                  │
│  yaml_list_tests(feature="播放")                                  │
│    → 按条件过滤的用例列表                                          │
│                                                                  │
│  yaml_run_batch(test_ids=["001","002",...])                       │
│    → {job_id, total_batches, status}                             │
│                                                                  │
│  yaml_get_status(job_id)                                         │
│    → {status, progress, current_batch, results}                   │
│    (轮询间隔 5s)                                                  │
│                                                                  │
│  yaml_cancel(job_id)                                             │
│    → {cancelled: true}                                           │
└───────────────────────────┬──────────────────────────────────────┘
                            │ MCP HTTP / stdio
┌───────────────────────────▼──────────────────────────────────────┐
│                    MCP Server (src/mcp/server.py)                 │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐                      │
│  │ yaml_list_tests  │  │ yaml_run_batch   │                      │
│  │ yaml_get_status  │  │ yaml_cancel      │                      │
│  └──────┬───────────┘  └────────┬─────────┘                      │
│         │                       │                                │
│         ▼                       ▼                                │
│  ┌──────────────┐     ┌─────────────────┐                        │
│  │ YamlIndex    │     │   JobManager    │  (移植自 deepin-mcp)    │
│  │ ──────────── │     │   ───────────── │                        │
│  │ load()       │     │   submit()      │                        │
│  │ query()      │     │   get_status()  │                        │
│  │ rebuild()    │     │   cancel()       │                        │
│  └──────────────┘     └────────┬────────┘                        │
│                                │                                 │
│                                ▼                                 │
│                       _execute_batch()                           │
│                         ├─ for batch in batches:                 │
│                         │    pytest.main([yaml/test_001.yaml,    │
│                         │                 yaml/test_002.yaml])   │
│                         │    → progress_callback(msg)            │
│                         │    → collect results                   │
│                         └─ aggregate → final report              │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 组件清单

| 组件 | 位置 | 类型 | 说明 |
|------|------|------|------|
| `YamlIndex` | `src/yaml_test/index.py` | **新增** | 索引加载、查询、重建 |
| `JobManager` | `src/mcp/jobs.py` | **新增** | 异步任务管理(移植 deepin-mcp) |
| MCP 工具(4个) | `src/mcp/server.py` | **修改** | 新增 4 个 `@mcp.tool` |
| `TestCase` 模型 | `src/yaml_test/parser.py` | **修改** | 新增 `description`/`module`/`feature`/`tags` 字段 |
| CLI `index` 命令 | `cli/main.py` + `cli/index.py` | **修改** | `youqu index --rebuild` |
| 骨架模板 | `cli/make.py` | **修改** | `_SAMPLE_YAML` 包含新字段 |
| 索引文件 | `autotest/yaml/index.yaml` | **新增** | 自动生成，不加入 git？ |

---

## 5. 详细设计

### 5.1 YAML Schema 扩展 (`parser.py`)

**改动**: 在 `TestCase` 模型中新增三个可选字段:

```python
class TestCase(BaseModel):
    model_config = ConfigDict(extra="allow")  # 保持 extra=allow 向后兼容

    name: str
    app: str = ""
    # ── 新增字段 ──
    description: str = ""  # 原始测试步骤和期望，用于 YAML 校对和验收参考
    module: str = ""       # 模块分类，如 "播放"、"设置"、"编辑"
    feature: str = ""      # 功能子类，如 "本地文件"、"在线流"
    tags: list[str] = Field(default_factory=list)  # 标签列表 ["L1", "smoke"]
    # ── 现有字段 ──
    screenshot: bool = False
    vars: dict[str, Any] = Field(default_factory=dict)
    ...
```

**向后兼容**: 旧 YAML 无这些字段时，`module=""`, `feature=""`, `tags=[]`。索引归类为 `uncategorized`。

**示例 YAML**:
```yaml
# test_music_play_001.yaml
name: "音乐-播放本地MP3"
description: |
  前置条件: 已安装音乐应用，本地有 MP3 文件

  测试步骤:
  1. 打开音乐应用
  2. 点击"本地歌曲"标签
  3. 双击第一首 MP3 歌曲

  预期结果:
  1. 音乐应用正常启动，显示主界面
  2. 切换到本地歌曲列表
  3. 开始播放歌曲，进度条出现
module: "播放"
feature: "本地文件"
tags: ["L1", "smoke"]
app: "deepin-music"
setup:
  - action: session_start
    command: "deepin-music"
steps:
  ...
```

### 5.2 索引系统 (`src/yaml_test/index.py`)

**索引文件格式** (`yaml/index.yaml`):

```yaml
# 自动生成，勿手动编辑
version: 1
generated_at: "2026-06-09T12:00:00"
tests:
  - file: test_music_play_001.yaml
    name: "音乐-播放本地MP3"
    description: "前置条件: 已安装音乐应用...\n测试步骤:\n1. 打开音乐应用\n..."
    module: "播放"
    feature: "本地文件"
    tags: ["L1", "smoke"]
    app: "deepin-music"
  - file: test_terminal_tab_003.yaml
    name: "终端-新建标签页"
    description: "测试步骤:\n1. 打开终端\n2. 点击+号新建标签页\n..."
    module: "标签管理"
    feature: "新建"
    tags: ["L2"]
    app: "deepin-terminal"
```

**ID 规则**: 从文件名推导，`test_music_play_001.yaml` → `test_music_play_001`。

**YamlIndex API**:

```python
class YamlIndex:
    """YAML test case index."""

    def __init__(self, yaml_dir: Path) -> None: ...

    def load(self) -> list[dict]:
        """加载 index.yaml。不存在则自动 rebuild。"""

    def rebuild(self) -> list[dict]:
        """扫描 yaml_dir 下所有 test_*.yaml，解析元数据，覆写 index.yaml。"""

    def query(
        self,
        app: str | None = None,
        module: str | None = None,
        feature: str | None = None,
        tags: list[str] | None = None,
    ) -> list[dict]:
        """按条件过滤。空条件 = 返回全部。"""

    def get_stats(self) -> dict:
        """返回统计: {total, modules: {name: count}, tags: {name: count}}"""
```

**索引更新触发时机**:
1. `youqu make <name>` — 生成骨架后自动 `rebuild()`
2. `youqu index --rebuild` — 手动重建
3. `youqu-case-generator` 生成新用例后 — 调用 `rebuild()`

**不自动重建的场景**: 不监控文件系统变更。用户手动编辑 YAML 后需手动 `rebuild` 或重新执行 `make`。

### 5.3 异步任务管理 (`src/mcp/jobs.py`)

**移植自** `deepin-mcp/src/deepin_mcp/orchestration/jobs.py`(260行)，关键适配:

| deepin-mcp | YouQu 适配 |
|-----------|-----------|
| `submit(fn, testcase)` | `submit(fn, test_ids)` — 传用例 ID 列表 |
| `TestRunner.run()` 作为 fn | `_execute_batches()` 作为 fn |
| `progress_callback(msg)` | 相同，报告 "batch 2/5: test_xxx_003 (3/5 in batch)" |
| `cancel_event` | 相同，批次间检查取消 |
| 单例 `AppContext.get().job_manager` | 模块级单例 `_job_manager` |

**JobStatus 状态机**(不变):

```
submit() → queued → running → completed/failed
                           ↘ cancelled
submit() → rejected (已有任务运行)
```

**关键行为**:
- `MAX_CONCURRENT = 1`: 同一时间只允许一个测试任务运行(UI 必须串行)
- 冲突处理: 新提交时若已有运行任务，返回 `status="rejected"` + `running_job_id`
- `CLEANUP_MAX_AGE = 3600`: 1小时后自动清理已完成任务
- `cancel()` 是协作式: 在批次间检查，当前批次内的 pytest session 继续完成
- `daemon=True`: 线程守护，MCP server 退出时自动清理

### 5.4 MCP 工具定义 (`src/mcp/server.py`)

#### 5.4.1 `yaml_list_tests`

```python
@mcp.tool
def yaml_list_tests(
    app: str = "",
    module: str = "",
    feature: str = "",
    tags: str = "",  # 逗号分隔的标签列表
) -> dict:
    """List available YAML test cases with optional filtering.

    Args:
        app: Filter by app name (e.g. 'deepin-music')
        module: Filter by module (e.g. '播放')
        feature: Filter by feature (e.g. '本地文件')
        tags: Comma-separated tags (e.g. 'L1,smoke')

    Returns:
        {
            "total": 15,
            "tests": [
                {
                    "id": "test_music_play_001",
                    "name": "音乐-播放本地MP3",
                    "description": "前置条件: 已安装音乐应用...\n测试步骤:\n1. 打开音乐应用\n...",
                    "module": "播放",
                    "feature": "本地文件",
                    "tags": ["L1", "smoke"],
                    "app": "deepin-music"
                },
                ...
            ],
            "stats": {
                "total": 15,
                "modules": {"播放": 5, "设置": 3},
                "tags": {"L1": 6, "L2": 9}
            }
        }
    """
```

**autotest 定位策略**:
- 优先从环境变量 `YOUQU_AUTOTEST_DIR` 获取
- 其次从 CWD 向上查找 `autotest/` 目录
- 最后从 `_PROJECT_ROOT / "autotest"` 查找

#### 5.4.2 `yaml_run_batch`

```python
@mcp.tool
def yaml_run_batch(
    test_ids: str,  # 逗号分隔的测试ID列表
    timeout_seconds: int = 0,  # 0=立即返回job_id，>0=阻塞等待
) -> dict:
    """Run a batch of YAML test cases asynchronously.

    Tests are split into batches of at most 5 and executed sequentially.
    Each batch runs as a separate pytest session.

    Args:
        test_ids: Comma-separated test IDs (e.g. 'test_play_001,test_play_002')
                  Use 'ALL' to run all YAML tests.
                  Use 'module:播放' to run all tests in a module.
                  Use 'tag:L1' to run all tests with a tag.
        timeout_seconds: Max seconds to wait for result.
            0 (default): return job_id immediately, poll via yaml_get_status.
            >0: block and wait up to this many seconds.

    Returns:
        If job accepted:
            {"job_id": "a1b2c3d4", "status": "queued", "total_batches": 3, "total_cases": 12}
        If another job running:
            {"success": false, "error": "Another job is running", "running_job_id": "x9y8z7"}
    """
```

**test_ids 格式**:
| 格式 | 含义 | 示例 |
|------|------|------|
| `test_xxx_001,...` | 显式 ID 列表 | `test_play_001,test_play_002` |
| `ALL` | 全部 YAML 用例 | `ALL` |
| `module:播放` | 某模块全部用例 | `module:播放` |
| `tag:L1` | 某标签全部用例 | `tag:L1,smoke` |

**批量切分逻辑**:
```python
def _split_batches(test_ids: list[str], max_per_batch: int = 5) -> list[list[str]]:
    return [test_ids[i:i+max_per_batch] for i in range(0, len(test_ids), max_per_batch)]
```

**执行流程**:
```python
def _execute_batches(batch_ids, yaml_dir, progress_callback, cancel_event):
    results = []
    for idx, batch in enumerate(batch_ids):
        if cancel_event.is_set():
            return {"status": "cancelled", "completed_batches": idx, ...}

        progress_callback(f"batch {idx+1}/{len(batch_ids)}: {batch[0]}..{batch[-1]}")

        # 构造 pytest 命令行 — 直接传文件路径而非 -k
        file_paths = [str(yaml_dir / f"{tid}.yaml") for tid in batch]
        cmd = [
            sys.executable, "-m", "pytest",
            "-c", str(yaml_dir.parent / "pytest.ini"),
            "--rootdir", str(yaml_dir.parent),
            "-q", "--tb=short",
            "--alluredir", str(yaml_dir.parent / "report" / f"batch_{idx+1}"),
        ] + file_paths

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        batch_result = _parse_pytest_output(proc)
        results.append(batch_result)

    return aggregate(results)
```

**为什么传文件路径而非 `-k`**:
- `-k` 匹配 test name(中文)，不可靠
- 传文件路径直接精确指定要运行的 YAML 文件
- pytest 的 `pytest_collect_file` hook 已验证路径在 `yaml_files` 目录下

#### 5.4.3 `yaml_get_status`

```python
@mcp.tool
def yaml_get_status(job_id: str) -> dict:
    """Get the status of a running or completed test job.

    Args:
        job_id: Job ID returned by yaml_run_batch.

    Returns:
        {
            "job_id": "a1b2c3d4",
            "status": "running",           # queued|running|completed|failed|cancelled
            "progress": "batch 2/5: test_play_003 (3/5 in batch)",
            "elapsed_ms": 45000,
            "total_batches": 5,
            "completed_batches": 1,
            "total_cases": 12,
            "results": {                   # 仅在 completed/failed 时返回
                "passed": 10,
                "failed": 1,
                "skipped": 1,
                "batches": [
                    {"batch": 1, "passed": 5, "failed": 0, ...},
                    ...
                ]
            }
        }
    """
```

#### 5.4.4 `yaml_cancel`

```python
@mcp.tool
def yaml_cancel(job_id: str) -> dict:
    """Cancel a running test job.

    Completes the current batch, then stops. Completed batches are preserved.

    Args:
        job_id: Job ID to cancel.

    Returns:
        {"job_id": "a1b2c3d4", "cancelled": true}
    """
```

### 5.5 CLI 命令扩展

#### 5.5.1 `youqu index` 命令

```bash
# 重建索引
youqu index --rebuild

# 列出所有用例 (按 app 目录)
youqu index --list -a apps/autotest_deepin_music

# 按条件过滤
youqu index --list --module 播放 --tag L1
```

**实现**: `cli/index.py` (~80行)，通过 `YamlIndex` 类实现。

#### 5.5.2 `cli/main.py` 修改

```python
# youqu index
p_index = sub.add_parser("index", help="Manage YAML test index")
p_index.add_argument("--rebuild", action="store_true", help="Rebuild index from YAML files")
p_index.add_argument("--list", action="store_true", help="List test cases")
p_index.add_argument("--app", default="", help="Filter by app")
p_index.add_argument("--module", default="", help="Filter by module")
p_index.add_argument("--tag", default="", help="Filter by tag")
```

### 5.6 骨架模板更新 (`cli/make.py`)

**改动**: `_SAMPLE_YAML` 模板加入 `module`/`feature`/`tags`:

```python
_SAMPLE_YAML = r"""name: "{name} 基础启动测试"
description: |  # TODO: 填写原始测试步骤和预期结果
  前置条件:

  测试步骤:
  1.

  预期结果:
  1.
module: ""       # TODO: 填写模块名，如 "播放"、"设置"
feature: ""      # TODO: 填写功能名，如 "本地文件"、"在线流"
tags: []          # TODO: 填写标签，如 ["L1", "smoke"]
app: "{name}"
...
"""
```

同时 `generate()` 在骨架生成后调用 `YamlIndex(yaml_dir).rebuild()`。

### 5.7 技能更新

#### 5.7.1 `youqu-case-generator` 技能

**改动点**:
1. 接受 `module`/`feature`/`tags`/`description` 参数
2. 生成的 YAML 模板包含这些字段，`description` 从 xlsx/csv 的"测试步骤"和"预期结果"列填充
3. 生成完成后调用 `YamlIndex.rebuild()` 或执行 `youqu index --rebuild`

**更新文件**: `~/.config/opencode/skills/youqu-case-generator/SKILL.md`
- 在 YAML 模板示例中添加 `description`/`module`/`feature`/`tags` 字段
- 在生成步骤中添加"生成后重建索引"步骤

#### 5.7.2 `youqu-case-runner` 技能

**改动点**: 执行流程从 CLI 改为 MCP 异步模式。

**旧流程**:
```
Step 5: bash("youqu run [args]") → 阻塞等待 → 解析输出
```

**新流程**:
```
Step 5a: yaml_list_tests(app, module, feature) → 确定要执行的用例
Step 5b: yaml_run_batch(test_ids) → 获取 job_id
Step 5c: while not done:
           yaml_get_status(job_id) → 报告进度
           sleep(5)
Step 5d: 汇总最终结果
```

**更新文件**: `~/.config/opencode/skills/youqu-case-runner/SKILL.md`
- Step 2 改为使用 `yaml_list_tests` 查询
- Step 3 解析意图支持 `module:`/`tag:` 前缀
- Step 5 改为 MCP 异步执行流程
- Step 6 改为解析 `yaml_get_status` 返回的结构化结果

### 5.8 文档更新

| 文件 | 改动 |
|------|------|
| `README.md` | MCP Server 功能表新增 4 个 YAML 工具 |
| `docs/` (VitePress) | 新增 "YAML 用例索引" 页面，更新 "MCP Server" 页面 |
| `AGENTS.md` | 新增 YAML 索引相关 memory entry |

---

## 6. 实施计划

### Phase 1: Schema + Index (可并行)

| # | 任务 | 文件 | 估时 |
|---|------|------|------|
| 1.1 | `TestCase` 模型添加 `description`/`module`/`feature`/`tags` | `src/yaml_test/parser.py` | 5min |
| 1.2 | 实现 `YamlIndex` 类 | `src/yaml_test/index.py` (新) | 30min |
| 1.3 | 更新骨架模板 `_SAMPLE_YAML` | `cli/make.py` | 5min |
| 1.4 | 骨架生成后自动 `rebuild()` | `cli/make.py` | 5min |
| 1.5 | 实现 `youqu index` CLI 命令 | `cli/index.py` (新) + `cli/main.py` | 30min |
| 1.6 | 更新 `youqu-case-generator` 技能 | `SKILL.md` | 15min |

### Phase 2: JobManager 移植 (可并行)

| # | 任务 | 文件 | 估时 |
|---|------|------|------|
| 2.1 | 移植 `JobManager` + `JobStatus` | `src/mcp/jobs.py` (新) | 30min |
| 2.2 | 适配 `submit()` 签名(传 test_ids 而非 testcase) | `src/mcp/jobs.py` | 10min |
| 2.3 | 实现 `_execute_batches()` | `src/mcp/jobs.py` | 20min |

### Phase 3: MCP 工具 (Phase 2 完成后)

| # | 任务 | 文件 | 估时 |
|---|------|------|------|
| 3.1 | `yaml_list_tests` 工具 | `src/mcp/server.py` | 20min |
| 3.2 | `yaml_run_batch` 工具 | `src/mcp/server.py` | 15min |
| 3.3 | `yaml_get_status` 工具 | `src/mcp/server.py` | 10min |
| 3.4 | `yaml_cancel` 工具 | `src/mcp/server.py` | 10min |
| 3.5 | 模块级 `_job_manager` 单例 + Lifespan 集成 | `src/mcp/server.py` | 10min |

### Phase 4: 技能 + 文档

| # | 任务 | 文件 | 估时 |
|---|------|------|------|
| 4.1 | 更新 `youqu-case-runner` 技能 | `SKILL.md` | 15min |
| 4.2 | 更新 `README.md` MCP 功能表 | `README.md` | 5min |
| 4.3 | 添加新 memory entry | (via `ctx_memory`) | 5min |

---

## 7. 迁移与向后兼容

### 7.1 旧 YAML 文件
- 无 `description`/`module`/`feature`/`tags` 字段 → 默认 `description=""`, `module=""`, `feature=""`, `tags=[]`
- 索引归类为 `module: "uncategorized"`
- 不影响执行

### 7.2 旧版 `youqu-case-runner` 用户
- 技能更新后自动使用新流程
- 无需手动迁移

### 7.3 现有 MCP 工具
- 不受影响，新增工具与旧工具隔离

### 7.4 index.yaml 在 git 中的策略
- **加入 `.gitignore`** 还是**纳入版本控制**?
- 建议**: 纳入版本控制**。原因：
  - 团队成员 checkout 后立即可查询用例
  - CI 不需要重建步骤(重建开销小但增加复杂度)
  - 手动编辑 YAML 后需要提交索引更新(或用 CI hook)
- 备选: `.gitignore` + CI 自动重建。初期纳入版本控制，后续根据团队反馈调整。

---

## 8. 测试策略

### 8.1 单元测试

| 测试对象 | 测试内容 |
|---------|---------|
| `TestCase` 模型 | 新字段默认值(`description` 多行字符串)、旧 YAML 解析兼容性 |
| `YamlIndex` | rebuild、query 各种过滤组合、stats 统计 |
| `JobManager` | submit/get_status/cancel 状态机、拒绝逻辑、清理 |
| `_split_batches` | 空列表、整除、余数边界 |

### 8.2 集成测试

| 场景 | 验证 |
|------|------|
| 新 YAML skeleton 包含新字段 | `youqu make test_app` 后检查生成文件包含 `description`/`module`/`feature`/`tags` |
| 索引重建 | `youqu index --rebuild` 后 index.yaml 内容正确 |
| 批量执行 1 个 batch | 5 个用例全部 PASS |
| 批量执行多个 batch | batch 间正确串行，进度回调调用 |
| 取消执行 | 当前 batch 完成后停止，保留已完成结果 |
| 旧 YAML 兼容 | 无 module 字段的 YAML 正常执行 |
| 冲突拒绝 | 两个 yaml_run_batch 同时提交，第二个 rejected |

### 8.3 E2E 测试

复用 `tests/e2e/autotest_menu/` 目录：
1. 执行 `yaml_list_tests` 验证查询
2. 执行 `yaml_run_batch` + `yaml_get_status` 轮询验证异步流程
3. 验证 `yaml_cancel` 取消

---

## 9. 风险与缓解

| 风险 | 影响 | 概率 | 缓解 |
|------|------|------|------|
| pytest subprocess 超时 | batch 卡死 | 中 | `subprocess.run(timeout=600)`，超时后标记 batch 失败 |
| index.yaml 与实际 YAML 不一致 | 查询结果不准 | 中 | `yaml_list_tests` 前检查 index 时间戳，过期自动重建 |
| 多 AI 客户端同时调用 | 第二个被拒绝 | 低 | 返回 `running_job_id`，AI 可提示用户等待 |
| fastmcp 版本不兼容 | MCP 工具无法注册 | 低 | 固定 `fastmcp` 版本依赖 |
| 中文 test name 在 pytest 输出中乱码 | 结果解析失败 | 低 | 设置 `PYTHONIOENCODING=utf-8` |

---

## 10. 开放问题

| # | 问题 | 选项 | 建议 |
|---|------|------|------|
| Q1 | `index.yaml` 是否纳入 git？ | A: 纳入 / B: .gitignore | **A: 纳入**，方便团队 |
| Q2 | autotest 目录定位策略？ | A: 环境变量 / B: CWD 查找 / C: 固定路径 | **A+B**: `YOUQU_AUTOTEST_DIR` 优先，否则 CWD 向上查找 |
| Q3 | `yaml_run_batch` 的 `timeout_seconds` 默认值？ | A: 0(立即返回) / B: 25(阻塞等) | **A: 0**，异步为主 |
| Q4 | batch 大小硬编码 5 还是可配置？ | A: 硬编码 / B: 可配置参数 | **B: 可配置**，默认 5，`yaml_run_batch(test_ids, batch_size=5)` |
| Q5 | 需要 `yaml_list_batches` 工具吗？(展示 batch 切分结果) | A: 需要 / B: 不需要 | **B: 不需要**，AI 从 total_batches/total_cases 即可判断 |
| Q6 | 是否需要实时日志流？ | A: 需要 / B: 不需要 | **B: 不需要**，轮询进度足够 |

---

## 附录 A: 与 deepin-mcp 的差异对比

| 维度 | deepin-mcp | YouQu |
|------|-----------|-------|
| **执行引擎** | 自有 TestRunner | 复用 pytest + StepExecutor |
| **测试格式** | YAML/JSON | YAML(首期) |
| **索引系统** | 无 | 新增 YamlIndex |
| **批量粒度** | 单个 YAML 文件 | 5 个 per batch(可配置) |
| **并发模型** | threading.Thread | 相同(移植) |
| **状态存储** | AppContext 单例 | 模块级单例 |
| **进度粒度** | 步骤级 | batch 级 + 用例级 |
| **报告** | 自有 JSON | Allure + pytest JSON |

## 附录 B: 涉及文件清单

```
修改文件:
  src/yaml_test/parser.py          — TestCase 模型新增 description/module/feature/tags 字段
  src/mcp/server.py                — 新增 4 个 MCP 工具 + JobManager 单例
  cli/main.py                      — 新增 index 子命令
  cli/make.py                      — 骨架模板更新 + 生成后 rebuild

新增文件:
  src/yaml_test/index.py           — YamlIndex 类
  src/mcp/jobs.py                  — JobManager + JobStatus
  cli/index.py                     — youqu index CLI 实现
  autotest/yaml/index.yaml         — 索引文件(自动生成)

技能更新:
  ~/.config/opencode/skills/youqu-case-generator/SKILL.md
  ~/.config/opencode/skills/youqu-case-runner/SKILL.md

文档更新:
  README.md                        — MCP 功能表
  (VitePress docs 后续)
```
