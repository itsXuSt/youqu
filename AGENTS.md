# YouQu (有趣) — AGENTS.md

Linux 桌面自动化测试框架，统信 Deepin/UOS 开源，GPL-2.0。
当前版本: v2.14.4，PyPI 包名: `youqu-framework`。

## 技术特点

**五大测试能力**: 桌面 UI (AT-SPI+Dogtail)、Web UI (Playwright)、DBus 接口、命令行、HTTP 接口。

**X11 + Wayland 双协议支持** — 框架核心差异点。键鼠操作在 X11 用 xdotool/pyautogui，Wayland 用 ydotool/D-Bus Autotool；窗口信息在 X11 用 xdotool+xwininfo，Wayland 用 libdtkwmjack (CTypes FFI)。`GlobalConfig.IS_WAYLAND` 是关键开关。

**CSV 驱动的标签管理系统** — 每个 APP 工程有一个 CSV 文件管理用例标签 (skip/fixed/removed/自定义标签/PMS用例ID)。`conftest.py` 在用例收集阶段自动解析 CSV 并应用标记。

**PMS 测试管理平台集成** — 测试结果可自动回填到 PMS (pms.uniontech.com)，支持从测试单/测试套件拉取关联用例执行。

**远程分布式执行** — 通过 SSH/SCP 分发代码到多台测试机，支持并行或分布式模式。

## 解决的问题

1. Linux 桌面应用缺乏统一自动化测试框架 — YouQu 提供了 AT-SPI 坐标/图像/OCR/DBus 多种定位方式
2. X11 向 Wayland 迁移期的兼容性 — 双协议支持避免测试框架需要重写
3. 大规模用例管理 — CSV 标签系统 + PMS 集成实现用例的精细化管理
4. 多机器执行 — 远程执行器支持分布式测试
5. 测试报告与数据回填 — Allure 报告 + JSON 报告 + PMS 自动回填

## AI 结合潜力分析

框架当前无任何 AI/LLM 集成代码。以下是可行的结合方向:

- **自然语言 → 用例生成**: 将 AI 生成的测试步骤翻译为 Widget 方法调用链，生成 `test_*.py` + CSV 标签文件
- **自愈元素定位**: AT-SPI 树结构变化时，LLM 基于上下文推断替代定位策略 (XPath/属性名/角色)
- **OCR 语义增强**: 当前 OCR 仅做精确文本匹配，LLM 可做模糊/语义匹配，提高稳定性
- **失败原因自动归类**: LLM 分析录屏/截图/日志自动归类失败原因 (环境/产品缺陷/脚本问题)
- **用例维护**: 从 PMS 需求描述或 PR 变更自动生成/更新测试用例
- **关键结合点**: `Src` 多继承基类、`DogtailUtils` 的 AT-SPI 树 API、`ButtonCenter` 坐标系统、`conftest.py` 的 CSV 标签引擎

## 项目结构

```
youqu/
├── manage.py           # 主入口 CLI，子命令: run/remote/startapp/pmsctl/csvctl/git
├── conftest.py         # pytest 根配置 (钩子、fixture、CSV标签解析、PMS回填)
├── apps/               # 测试用例目录 (pytest testpaths)，每个子目录是一个 APP 工程
├── src/                # 核心框架
│   ├── __init__.py     # Src 多继承基类 (CmdCtl+ImageUtils+FileCtl+ShortCut+Calculate+OCR)
│   ├── dogtail_utils.py    # AT-SPI 元素定位 (X11/Wayland)
│   ├── button_center.py    # 埐标定位系统 (基于 ui.ini 配置)
│   ├── mouse_key.py        # 键鼠操作 (xdotool/ydotool)
│   ├── image_utils.py      # 图像识别 (OpenCV，支持 RPC)
│   ├── ocr_utils.py        # OCR 文字识别 (PaddleOCR RPC，链式调用)
│   ├── assert_common.py    # 统一断言 (图像/OCR/元素/文件/进程)
│   ├── dbus_utils.py       # DBus 接口测试
│   ├── webui.py            # Web UI 自动化 (Playwright)
│   ├── cmdctl.py           # 命令执行控制
│   ├── requestx.py          # HTTP 请求
│   ├── rtk/                # 运行时: local_runner, remote_runner
│   ├── pms/                # PMS 集成: send2pms, suite, task, pms2csv, csv2pms
│   ├── plugins/            # pytest 插件 (emoji_hooks, allure_report_extend)
│   ├── remotectl/          # SSH 远程控制
│   ├── git/                # Git 子命令 (clone/commit统计/健康检查)
│   ├── depends/            # 内嵌第三方库 (dogtail, sniff, wayland_autotool 等)
│   └── utils/              # 环境部署脚本
├── cli/                  # CLI 命令 (youqu console_scripts)
│   ├── main.py            # argparse 路由入口
│   ├── make.py            # youqu make 骨架生成
│   └── run.py             # youqu run 执行逻辑
├── plugin/               # pytest 插件 (entry_points.pytest11)
│   └── __init__.py        # sys.path 注入 + 环境变量
├── setting/            # 配置
│   ├── globalconfig.py  # 全局配置加载器 (读取 globalconfig.ini)
│   ├── globalconfig.ini  # 主配置文件 (12 个 section)
│   ├── skipif.py         # 条件跳过逻辑
│   ├── pylintrc.cfg      # pylint 配置
│   └── template/app_template/  # APP 工程脚手架模板 (PO 设计)
├── docs/               # VitePress 文档站点
├── env.sh              # 环境部署脚本 (安装系统依赖 + Python 包)
├── publish.sh          # PyPI 发布脚本
├── pytest.ini          # pytest 配置: testpaths=apps, 隐含参数
├── ruff.toml           # Ruff lint 配置
└── pyproject.toml      # 包元数据 (hatchling 构建)
```

## 命令

### CLI 命令 (pip install youqu-framework 后可用)
```bash
youqu make <name>                              # 生成 autotest/ 骨架
youqu run                                       # 执行 autotest/ 下测试
youqu run -k "keyword"                          # 关键词过滤 (透传 pytest)
youqu run --alluredir=./report                  # 覆盖报告路径
youqu mcp                                       # 启动 MCP server (stdio)
youqu mcp --transport http --host 0.0.0.0 --port 8066  # HTTP 模式
youqu startproject <name>                       # 创建项目 (PO 模式脚手架)
```

### 测试执行 (manage.py，传统流程)
```bash
youqu manage.py run                           # 本地执行 (读取 globalconfig.ini 配置)
youqu manage.py run -a apps/autotest_xxx       # 指定 APP 工程
youqu manage.py run -k "keyword"               # 按关键词过滤
youqu manage.py run -t "L1 or smoke"           # 按标签过滤 (支持 and/or/not)
youqu manage.py remote                        # 远程分布式执行
youqu manage.py run --noskip                   # 忽略所有 skip 标记
youqu manage.py run --ifixed yes              # 忽略 fixed 标记 (fixed-不生效)
```

### 工程管理
```bash
youqu manage.py startapp autotest_deepin_xxx   # 创建 APP 工程 (PO 模式脚手架)
youqu manage.py pmsctl                         # PMS 数据管理
youqu manage.py csvctl                         # CSV 标签管理
youqu manage.py git                            # Git 子项目操作
```

### 环境与代码检查
```bash
bash env.sh                                    # 部署环境 (pipenv 虚拟环境)
bash env.sh -p PASSWORD                        # 指定 sudo 密码
bash env.sh -D                                 # 开发模式 (直接 pip install)
ruff check .                                   # lint
ruff format .                                  # format
src/utils/pylint.sh apps/autotest_xxx          # pylint HTML 报告
```

### 构建/发布
```bash
python3 -m build                              # 构建 wheel
twine upload dist/*                            # 发布到 PyPI
```

## 关键约定

### 用例命名 (强制)
函数名和文件名必须遵循 `test_<功能名>_<3位ID>` 格式，且两者 ID 必须一致。
不一致的用例会被框架自动 skip。例如: `test_music_001` 对应 `test_music_001.py`。

### APP 工程 PO 模式
通过 `startapp` 创建的工程遵循 Page Object 设计:
```
apps/autotest_xxx/
├── config.py              # 应用配置
├── xxx.csv                 # CSV 标签管理
├── xxx_assert.py           # 自定义断言 (继承 AssertCommon)
├── conftest.py             # 应用级 fixture
├── case/
│   ├── base_case.py        # 用例基类 (继承 AssertCommon)
│   └── test_xxx_001.py     # 具体用例
└── widget/
    ├── base_widget.py      # Widget 基类 (继承 Src)
    ├── xxx_widget.py       # 应用 Widget (封装 dog/button_center 操作)
    ├── ui.ini              # 控件坐标配置
    └── pic_res/            # 模板图片
```

继承链: `Src → BaseWidget → XxxWidget` (方法层)，`AssertCommon → XxxAssert → BaseCase → TestXxx` (用例层)。

### CSV 标签格式
CSV 文件与 APP 工程同名 (去掉前缀)。列: `ID, skip_reason, fixed, removed, PMS用例ID, 自定义标签...`。
- `skip-原因`: 跳过用例
- `fixed-版本`: 标记已修复 (默认会覆盖 skip)
- `removed-原因`: 从执行列表移除
- `skipif_<方法>-<参数>`: 条件跳过 (定义在 `setting/skipif.py`)

### 框架 API 导入
```python
from src import Src, OCR, MouseKey, DbusUtils, AssertCommon, CmdCtl, log
from setting import conf  # GlobalConfig 短别名
```

### pytest 隐含配置 (pytest.ini)
自动生效: `-s -vv --no-header --show-capture=no --tb=auto -r fEs --continue-on-collection-errors --ignore=src,setting,public`。测试路径: `apps/`。最低 pytest 版本: 6.2.5。

### 代码风格
Ruff: line-length=100, 4-space indent, Python 3.7+。仅启用 E4/E7/E9/F 规则 (大量 F 规则被 ignore)。
注意: 框架核心代码 (`src/`, `conftest.py`) 在文件头大量使用 `# pylint: disable`。

### 环境要求
- Python >= 3.6 (ruff target py37)
- 需要桌面环境 (X11 或 Wayland)，不能在 headless 下运行 UI 测试
- DISPLAY=:0 在 `conftest.py` 中硬编码
- 依赖通过 `env.sh` 安装 (无 requirements.txt / Pipfile / poetry.lock)
- 可选依赖: letmego (重启类场景)

### 远程执行
`manage.py remote` 通过 SSH 分发代码，`--slaves` 参数格式: `user@ip:password`，多台用 `/` 分隔。
