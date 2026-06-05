# PRD: YouQu CLI 独立化 + 依赖声明

> 版本: 1.0
> 日期: 2026-06-05
> 状态: 已确认

## 1. 背景与目标

### 1.1 问题

1. **依赖未声明**: `pyproject.toml` 的 `dependencies = []` 为空，所有 pip 包通过 `env.sh` + pipenv 安装，无法通过 `pip install youqu-framework` 自动解决依赖。
2. **CLI 入口缺失**: 当前 `youqu` 命令是一个 pipenv wrapper shell 脚本，不是 Python console_scripts。`manage.py` 依赖项目目录结构，无法从安装包直接执行。

### 1.2 目标

1. `pip install youqu-framework` 自动安装所有 pip 依赖。
2. `youqu make <name>` 在任意项目目录生成独立的 `autotest/` 测试骨架。
3. `youqu run` 在任意目录执行 `autotest/` 下的测试用例。
4. 新流程与现有流程完全并行，互不影响。

### 1.3 不做的事

- 不改造现有 `manage.py` / `LocalRunner` / `RemoteRunner`。
- 不改造根 `conftest.py`（CSV 标签引擎、PMS 回填等）。
- 不改造 `apps/` 目录结构和 `youqu-startproject`。
- 不移除 `env.sh`（保留系统级 deb 包安装）。

## 2. 架构设计

### 2.1 新旧流程并行

```
旧流程 (不变):
  youqu manage.py run -a apps/autotest_xxx
    → manage.py → SystemPath → conftest.py (CSV+PMS+录屏) → LocalRunner → pytest

新流程 (AI 自动化):
  youqu make terminal
    → 生成 autotest/ 骨架 (无 CSV, 无 PMS)

  AI skill → 读取骨架 + AT-SPI → 生成 case/test_terminal_001.py

  youqu run
    → 找到 autotest/
    → pytest plugin 自动加载: sys.path 注入 + 环境变量
    → 执行 case/ 下的 test_*.py
    → allure 报告到 autotest/report/
```

### 2.2 目录结构

```
youqu/                          # 安装后 in site-packages/youqu/
├── cli/                        # [新增] CLI 命令模块
│   ├── __init__.py
│   ├── main.py                 # argparse 路由入口 (youqu console_scripts)
│   ├── make.py                 # youqu make 模板生成
│   └── run.py                  # youqu run 执行逻辑
├── plugin/                     # [新增] pytest 插件
│   └── __init__.py             # pytest plugin hooks (sys.path + env)
├── src/                        # 不变 — 核心框架
├── setting/                    # 不变 — 配置加载
├── startproject.py             # 不变 — youqu-startproject (旧命令)
├── conftest.py                 # 不变 — 根级 conftest (仅 manage.py run 加载)
├── manage.py                   # 不变 — 旧入口
└── pytest.ini                  # 不变 — 旧 pytest 配置
```

### 2.3 新增文件清单

| 文件 | 职责 | 行数 (估计) |
|------|------|------------|
| `youqu/plugin/__init__.py` | pytest plugin: sys.path 注入 + 环境变量 | ~30 |
| `youqu/cli/__init__.py` | 包初始化 (空) | ~1 |
| `youqu/cli/main.py` | argparse 子命令路由 | ~50 |
| `youqu/cli/make.py` | youqu make 模板生成 | ~150 |
| `youqu/cli/run.py` | youqu run 执行逻辑 | ~40 |

### 2.4 修改文件清单

| 文件 | 改动内容 |
|------|----------|
| `pyproject.toml` | 填充 dependencies、新增 scripts、新增 entry-points.pytest11 |

## 3. 详细设计

### 3.1 pyproject.toml

```toml
[project]
name = "youqu-framework"
version = "2.15.0"
dependencies = [
    "funnylog",
    "pytest>=6.2.5",
    "allure-pytest==2.9.45",
    "allure-custom",
    "image-center",
    "pdocr-rpc",
    "PyAutoGUI==0.9.53",
    "pyscreeze==0.1.28",
    "pytest-rerunfailures==10.2",
    "pytest-timeout==2.1.0",
    "tomli; python_version < '3.11'",
]

[project.optional-dependencies]
webui = ["playwright"]
remote = ["zerorpc"]
mcp = ["fastmcp", "httpx"]

[project.scripts]
youqu = "youqu.cli.main:main"
youqu-startproject = "youqu.startproject:cli"

[project.entry-points.pytest11]
youqu = "youqu.plugin"
```

**设计决策**:
- `youqu` console_scripts 指向 `youqu.cli.main:main`。
- pytest plugin 通过 `entry_points.pytest11` 注册为 `youqu.plugin`。pytest 启动时自动加载，无论从哪个目录运行 pytest。
- 系统级 deb 包（python3-gi, python3-pyatspi 等）不在 dependencies 中，仍由 `env.sh` 安装。

### 3.2 youqu/plugin/__init__.py — pytest plugin

**职责 (最小化，3 个)**:

1. `sys.path` 注入 — 让 `from src import Src` 在任何目录工作
2. 环境变量设置 — `DISPLAY=:0`, `XAUTHORITY`
3. funnylog 初始化

**不包含**: CSV 标签引擎、PMS 回填、emoji hooks、录屏、allure 动态标记、自定义 pytest options（这些属于根 `conftest.py`，仅在 `manage.py run` 流程中加载）。

```python
import sys
import os
from pathlib import Path

_YOUQU_PKG = Path(__file__).resolve().parent.parent  # site-packages/youqu/


def pytest_configure(config):
    _inject_paths()
    _setup_env()


def _inject_paths():
    for p in (
        _YOUQU_PKG,
        str(_YOUQU_PKG / "setting"),
        str(_YOUQU_PKG / "src" / "depends"),
    ):
        if p not in sys.path:
            sys.path.insert(0, str(p))


def _setup_env():
    os.environ.setdefault("DISPLAY", ":0")
    os.environ.setdefault(
        "XAUTHORITY", f"{os.path.expanduser('~')}/.Xauthority"
    )
```

### 3.3 youqu/cli/main.py — CLI 入口

子命令:

| 命令 | 描述 | 委托 |
|------|------|------|
| `youqu make <name>` | 生成 autotest/ 骨架 | `cli.make:generate` |
| `youqu run [args...]` | 执行测试 | `cli.run:run` |
| `youqu mcp` | 启动 MCP server | `src.mcp.server:start` |

`youqu mcp` 参数:

| 参数 | 默认值 | 描述 |
|------|--------|------|
| `--transport` | `stdio` | 传输协议 (`stdio`/`sse`/`http`) |
| `--host` | `127.0.0.1` | 绑定地址 (仅 sse/http) |
| `--port` | `8000` | HTTP 端口 (仅 sse/http) |

`youqu run` 参数 (最小化子集):

| 参数 | 描述 |
|------|------|
| `-a, --app` | 覆盖 autotest/ 路径 |
| 其他 | 全部透传给 pytest (`-k`, `--alluredir`, `-v` 等) |

### 3.4 youqu/cli/make.py — youqu make

**模板生成规则**:

`youqu make <name>` 在当前目录生成 `autotest/`:

```
autotest/
├── conftest.py              # 空（AI 模式不需要 CSV 标签引擎）
├── pytest.ini               # testpaths=case, 精简 addopts
├── config.ini               # 应用配置 (GetCfg 读取)
├── ui.ini                   # 按钮坐标 (ButtonCenter 读取)
├── case/
│   ├── __init__.py          # from .base_case import BaseCase
│   ├── base_case.py         # from src.assert_common import AssertCommon
│   └── test_{name}_001.py  # 示例占位用例
├── widget/
│   ├── __init__.py          # from .{name}_widget import {Camel}Widget
│   ├── base_widget.py       # from src import Src
│   ├── {name}_widget.py     # 应用级 Widget（空）
│   └── pic_res/             # 模板图片目录
└── report/                   # pytest 生成 (默认 allure 输出)
```

**与现有 startproject 的关键区别**:

| 维度 | startproject | youqu make |
|------|-------------|------------|
| 输出位置 | `apps/autotest_xxx/` | `autotest/` (CWD) |
| 导入方式 | `from apps.xxx.case import BaseCase` | `from .base_case import BaseCase` |
| config.py | 继承 `_GlobalConfig` | 不需要，用 `config.ini` + GetCfg |
| CSV | 需要 | 不需要 |
| pytest root | 项目根目录 | `autotest/` 目录本身 |
| PMS | 集成 | 不集成 |

### 3.5 youqu/cli/run.py — youqu run

**执行逻辑**:

1. 查找 `autotest/` 目录:
   - `-a/--app` 指定 → 使用指定路径
   - CWD 下有 `autotest/` → 使用 CWD/autotest
   - CWD 下有 `case/` → 使用 CWD（autotest 本身就是 CWD）
   - 都没有 → 报错退出

2. 构建 pytest 命令:
   ```
   pytest -c <autotest>/pytest.ini --rootdir <autotest> --alluredir <autotest>/report [用户参数...]
   ```

3. 默认 allure 报告目录为 `autotest/report/`（可通过 `--alluredir` 覆盖）。

4. 切换到 `autotest/` 目录，调用 `pytest.main()`。

**不做的事**:
- 不经过 `manage.py`
- 不加载根 `conftest.py`
- 不处理 CSV / PMS / 录屏

### 3.6 env.sh 拆分

`env.sh` 保留系统级 deb 包安装，去掉 pip 包安装：

```bash
# 仅保留 apt install 部分
sudo apt install -y \
    python3-gi python3-gi-cairo gir1.2-atspi-2.0 \
    python3-pyatspi python3-dbus python3-cairo \
    python3-pil python3-opencv \
    python3-tk python3-pexpect python3-ptyprocess \
    scrot xdotool wmctrl
```

pip 包由 `pip install youqu-framework` 根据 `pyproject.toml` 自动解决。

## 4. 兼容性

| 现有功能 | 影响 |
|----------|------|
| `youqu manage.py run` | 无影响 — 不经过新代码 |
| `youqu-startproject` | 无影响 — 独立 console_scripts |
| `apps/` 目录结构 | 无影响 |
| CSV 标签格式 | 无影响 |
| `from src import Src` | 无影响 — pytest plugin 自动注入 sys.path |
| `publish.sh` | 简化为 `rm -rf dist/ && python3 -m build` |

## 5. 验收标准

- [ ] `python3 -m build` 构建 wheel 成功
- [ ] `pip install dist/*.whl` 安装成功，`youqu --help` 正常输出
- [ ] `youqu make terminal` 生成 `autotest/` 骨架，结构完整
- [ ] `autotest/case/base_case.py` 中 `from src.assert_common import AssertCommon` 可正常导入
- [ ] `autotest/widget/base_widget.py` 中 `from src import Src` 可正常导入
- [ ] `youqu run` 能收集并执行 `autotest/case/` 下的测试用例
- [ ] `youqu run -k test_terminal` 关键词过滤正常
- [ ] `youqu run --alluredir=./my-report` 报告路径覆盖正常
- [ ] `youqu run` 默认生成 allure 报告到 `autotest/report/`
- [ ] `youqu mcp --transport http --host 0.0.0.0 --port 8066` 启动正常
- [ ] 现有 `youqu manage.py run -a apps/autotest_xxx` 不受影响
