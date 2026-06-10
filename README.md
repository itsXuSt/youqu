<p align="center">
  <a href="https://linuxdeepin.github.io/youqu">
    <img src="./docs/assets/logo.png" width="100" alt="YouQu">
  </a>
</p>
<p align="center">
    <em>YouQu（有趣），一个使用简单且功能强大的自动化测试框架。</em>
</p>

[![GitHub issues](https://img.shields.io/github/issues/linuxdeepin/youqu?color=%23F79431)](https://github.com/linuxdeepin/youqu/issues)
[![PyPI](https://img.shields.io/pypi/v/youqu?style=flat&logo=github&link=https%3A%2F%2Fpypi.org%2Fproject%2Fyouqu%2F&color=%23F79431)](https://pypi.org/project/youqu/)
![Static Badge](https://img.shields.io/badge/UOS%2FDeepin/openEuler/openAnolis-Platform?style=flat&label=OS&color=%23F79431)

[![Downloads](https://static.pepy.tech/badge/youqu)](https://pepy.tech/project/youqu)
[![Hits](https://hits.sh/github.com/linuxdeepin/youqu.svg?style=flat&label=visitors&color=blue)](https://github.com/linuxdeepin/youqu)

---

**深度社区：<a href="https://github.com/linuxdeepin/youqu" target="_blank">linuxdeepin</a> | <a href="https://gitee.com/deepin-community/youqu" target="_blank">deepin-community</a>**

**欧拉社区：<a href="https://gitee.com/src-openeuler/youqu" target="_blank">openEuler</a>**

**龙晰社区：<a href="https://gitee.com/anolis/youqu" target="_blank">openAnolis</a>**

**官方文档：<a href="https://youqu.uniontech.com" target="_blank">https://youqu.uniontech.com</a>**

**欢迎加入 [YouQu官方兴趣小组](https://youqu.uniontech.com/SIG.html)**

---

YouQu（有趣）是统信公司（Deepin/UOS）开源的一个 Linux 操作系统的自动化测试框架，支持多元化元素定位和断言、用例标签化管理和执行、强大的日志和报告输出等特色功能，同时完美兼容 X11、Wayland 显示协议，环境部署简单，操作易上手。🔥

## YouQu 能做什么

- [X]  💻 Linux 桌面应用 UI 自动化测试
- [X]  🌏 Web UI 自动化测试
- [X]  🚌 Linux DBus 接口自动化测试
- [X]  🚀 命令行自动化测试
- [X]  🕷️ HTTP 接口自动化测试

## 快速开始

### 安装

从 PyPI 安装:

```shell
$ sudo pip3 install youqu-framework
```

> 验证安装：`youqu --help` 列出所有子命令，`youqu --version` 显示版本号。
> 如果遇到 `error: externally-managed-environment`，加上 `--break-system-packages`（虚拟环境则无需）。
> 升级或重装时需加 `--force-reinstall`，否则同版本号会被 pip 跳过。

<details>
    <summary><b>不加 sudo ?</b></summary>

---

不加 sudo 也可以：

```shell
pip3 install youqu-framework
```

但可能出现 `youqu-startproject` 命令无法使用；

这是因为不加 `sudo` 时，`youqu-startproject` 命令会生成在 `$HOME/.local/bin` 下，

而此路径可能不在环境变量（`PATH`）中，因此您需要添加环境变量：

```shell
export PATH=$PATH:$HOME/.local/bin
```

---

</details>

### 创建项目

您可以在任意目录下，使用 `youqu-startproject` 命令创建一个项目：

```shell
$ youqu-startproject my_project
```

注意：所有命令不要以 `root` 用户执行！

如果 `youqu-startproject` 后面不加参数，默认的项目名称为：`youqu` ；

![](./docs/assets/install.gif)

### 编写测试用例

YouQu 支持 **YAML** 和 **Python** 两种方式编写测试用例，同一个 `run` 命令统一执行：

```
youqu-startproject my_project
          |
   cd my_project
          |
   +------+-------+
   |              |
YAML 路径      Python 路径
声明式/AI友好   传统PO模式
   |              |
youqu make    youqu manage.py
   <name>      startapp <name>
   |              |
autotest/yaml/ apps/autotest_xxx/
├── elements   ├── widget/
│   .yaml      ├── case/
└── test_*.    └── ui.ini
    yaml
   |              |
   +------+-------+
          |
youqu manage.py run
```

#### YAML 路径（推荐 AI 用户）

声明式、无需编写 Python 代码，AI 客户端可直接通过 MCP 工具获取 AT-SPI 元素树并生成 YAML 用例：

```shell
$ youqu make my_app                    # 生成 autotest/，默认 YAML 格式
$ youqu make my_app --format all       # 同时生成 YAML + Python
```

YAML 用例将所有 UI 元素集中注册在 `autotest/yaml/elements.yaml`，测试用例通过 `ref` 引用元素，使用 `action` 声明操作、`assert` 声明断言。

#### Python 路径（传统 PO 模式）

适合需要复杂逻辑、自定义断言的场景，遵循 Page Object 设计模式：

```shell
$ youqu manage.py startapp autotest_deepin_some      # 创建 APP 工程（Python）
$ youqu make my_app --format py                       # 或通过 make 生成
```

自动创建的 APP 工程：

```shell
my_project
├── apps
│   ├── autotest_deepin_some
│   │   ├── widget/          # 元素操作层
│   │   ├── case/            # 测试用例层
│   │   ├── ui.ini           # 控件坐标配置
│   │   └── xxx.csv          # 标签管理
```

继承链：`Src → BaseWidget → XxxWidget`（方法层），`AssertCommon → XxxAssert → BaseCase → TestXxx`（用例层）。

> **在你的远程 Git 仓库中，只需要保存 APP 工程这部分代码即可。** `apps` 目录下可以存在任意多个 APP 工程。

### 系统依赖

YouQu 需要以下系统包：

| 包名 (Debian/Ubuntu) | 用途 |
|----------------------|------|
| `python3-pip` | Python 包管理 |
| `python3-tk` | Tkinter GUI |
| `scrot` | 屏幕截图 |
| `python3-opencv` | 图像识别 |
| `python3-pyatspi` | AT-SPI 辅助功能 Python 绑定 |
| `gir1.2-atspi-2.0` | AT-SPI GObject 内省 |
| `libatk-adaptor` | AT 适配器 |
| `at-spi2-core` | AT-SPI 核心 |
| `openjdk-11-jdk-headless` | Java（Allure 报告生成必需） |

> **RHEL/openEuler**: 使用对应的包名，如 `java-11-openjdk-headless`、`python3-tkinter`、`opencv` 等。

一键部署脚本：

```shell
$ cd my_project
$ bash env.sh
# 默认密码: 1；
# 指定密码: bash env.sh -p ${my_password}；
# 或修改 setting/globalconfig.ini 中 PASSWORD 配置项。
```

`env.sh` 会自动安装系统依赖、pip 包、配置 SSH 和辅助功能。

> **桌面环境要求**: 需要运行中的 X11 或 Wayland 桌面会话（`DISPLAY=:0`），`~/.Xauthority` 文件存在，辅助功能已开启。

可选功能依赖：

| 功能 | 安装方式 |
|------|----------|
| Web UI 自动化 | `pip install youqu-framework[webui]` + `playwright install chromium` |
| 远程执行 | `pip install youqu-framework[remote]`，需 `sshpass` |
| MCP Server | `pip install youqu-framework[mcp]`，需 Python >= 3.10 |
| Wayland 支持 | 额外需要 `g++ cmake qt5-default libkf5wayland-dev wl-clipboard` 等编译依赖 |

### 运行测试

在项目根目录下有一个 `manage.py` ，它是执行器入口，提供了本地执行、远程执行等的功能。

#### 本地执行

```shell
$ youqu manage.py run
```

> **autotest/ 项目**（通过 `youqu make` 生成的 YAML/Python 项目）也可以直接使用 `youqu run`，更轻量，无需 `manage.py`。

在一些 CI 环境下使用命令行参数会更加方便：

```shell
$ youqu manage.py run -a apps/autotest_deepin_some -k "xxx" -t "yyy"
```

更多用法可以使用 `-h` 或 `--help` 查看。

通过配置文件 [setting/globalconfig.ini](https://github.com/linuxdeepin/youqu/blob/master/setting/globalconfig.ini) 也可以配置执行的各项参数。

#### 远程执行

远程执行就是用本地作为服务端控制远程机器执行，远程机器执行的用例相同。

使用 `remote` 命令：

```shell
$ youqu manage.py remote
```

#### 生成报告

测试执行后会生成 Allure 原始数据（`autotest/report/`），使用 `youqu report` 转为 HTML：

```shell
$ youqu report                  # 生成 HTML 到 autotest/report/allure_html/
$ youqu report --clean          # 清除旧报告后重新生成
$ youqu report --serve          # 生成后启动 HTTP 服务，浏览器直接查看
```

> 需要 Java 运行环境（`openjdk-11-jdk-headless`），`youqu doctor` 可自动安装。

---

## AI 集成

### MCP Server

YouQu 内置 MCP (Model Context Protocol) Server，将桌面 UI 自动化能力暴露为 MCP 工具，
使 AI 客户端（Claude、OpenCode 等）能够直接操控测试机上的桌面应用。

#### 功能概览

| 工具组 | 能力 | 示例 |
|--------|------|------|
| **AT-SPI 操作** | 元素查找、点击、输入、滚动、悬停 | 点击按钮、输入文本、展开菜单 |
| **键盘鼠标** | 按键、快捷键、点击、移动 | Enter、Ctrl+C、鼠标左键 |
| **窗口管理** | 窗口列表、激活、关闭、最大化/最小化 | 切换窗口、关闭弹窗 |
| **截图** | 全屏截图并保存 | 保存当前屏幕到证据目录 |
| **进程管理** | 查询进程、终止进程（保护关键进程） | 关闭应用进程 |
| **系统命令** | 执行只读命令（ps、gsettings 等） | 查询系统设置 |
| **VLM 视觉** | 视觉定位元素、视觉断言、自主测试 | "点击桌面左下角的终端图标" |
| **YAML 测试执行** | 用例查询、异步批量执行、进度轮询 | 按模块/标签筛选用例，分批执行 |

#### 安装依赖

MCP Server 为可选功能，需要 Python >= 3.10：

```shell
pip3 install youqu-framework[mcp]
```

#### VLM 配置

编辑 `setting/globalconfig.ini`，启用 VLM 并配置后端 API：

```ini
[vlm]
VLM_ENABLED = true
VLM_BASE_URL = https://api-inference.modelscope.cn/v1/
VLM_MODEL = Qwen/Qwen3-VL-8B-Instruct
VLM_API_KEY = your-api-key
```

VLM 需要 OpenAI 兼容的视觉语言模型 API（Ollama、ModelScope、vLLM 等），框架不内置模型。

#### 启动 MCP Server

**stdio 模式**（本地子进程）：

```shell
youqu mcp
```

适用于本地 AI 客户端通过 stdio 管道连接。

**Streamable HTTP 模式**（远程连接）：

```shell
youqu mcp --transport http --host 0.0.0.0 --port 8000
```

CLI 参数说明：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--transport` | `stdio` | `stdio`（本地子进程）/ `sse`（HTTP+SSE）/ `http`（Streamable HTTP，推荐远程） |
| `--host` | `127.0.0.1` | 监听地址，远程连接需设为 `0.0.0.0` |
| `--port` | `8000` | 监听端口 |

#### 客户端连接配置

**Claude**（原生支持 HTTP）：

```bash
claude mcp add --transport http youqu http://192.168.1.100:8000/mcp
```

**OpenCode** — 在项目 `opencode.json` 中配置 MCP server：

```json
{
  "mcp": {
    "youqu-mcp": {
      "enabled": true,
      "type": "remote",
      "url": "http://127.0.0.1:8066/mcp"
    }
  }
}
```

连接远程测试机时改为对应的 IP 和端口。

**SSH 隧道**（安全内网连接）：

无需在测试机暴露端口，通过 SSH 隧道转发：

```shell
ssh -L 8000:localhost:8000 user@test-machine
```

然后本地客户端连接 `http://127.0.0.1:8000/mcp`。

#### 客户端兼容矩阵

| AI 客户端 | stdio | Streamable HTTP |
|-----------|:-----:|:---------------:|
| Claude | ✅ | ✅ |
| OpenCode | ✅ | ✅ |

#### YAML 批量执行

MCP Server 支持异步批量执行 YAML 用例，AI 客户端无需等待全部完成：

| MCP 工具 | 用途 |
|----------|------|
| `yaml_list_tests` | 按应用/模块/标签查询用例列表 |
| `yaml_run_batch` | 提交批量执行任务，返回 `job_id`，立即返回 |
| `yaml_get_status` | 轮询任务进度（queued → running → completed/failed） |
| `yaml_cancel` | 取消任务（完成当前批次后停止） |

典型流程：

```
yaml_list_tests(app="deepin-music", module="播放")
    → 筛选需要执行的用例
yaml_run_batch(test_ids="test_001,test_002", batch_size=5)
    → job_id: "a1b2c3d4"
yaml_get_status(job_id="a1b2c3d4")  # 每 5s 轮询
    → {status: "running", progress: "batch 2/3"}
    → {status: "completed", result: {passed: 10, failed: 1}}
```

### 安装技能

YouQu 内置 AI 技能文件，供 Claude、OpenCode 等 AI 客户端使用。

安装方式一：通过 `youqu doctor` 交互式安装：

```shell
$ youqu doctor
```

doctor 会在所有检查完成后，检测到内置技能文件并提示您选择 AI 客户端，
自动将技能安装到对应目录：

| AI 客户端 | 安装目录 |
|-----------|----------|
| Claude | `~/.claude/skills/` |
| OpenCode | `~/.config/opencode/skills/` |

安装方式二：手动复制：

```shell
# 查找技能文件路径
python3 -c "import youqu; from pathlib import Path; print(Path(youqu.__file__).parent / 'skills')"

# 复制到对应客户端目录
cp -r $(python3 -c "import youqu; from pathlib import Path; print(Path(youqu.__file__).parent / 'skills')")/* ~/.claude/skills/
```

安装后重启 AI 客户端即可加载技能。

### 常用命令

供 AI 客户端和 CI 环境使用的 CLI 命令：

| 命令 | 用途 |
|------|------|
| `youqu run` | 执行 `autotest/` 下测试，自动查找 pytest.ini、生成 Allure 报告 |
| `youqu run -k "keyword"` | 按关键词过滤执行 |
| `youqu report` | 将 Allure 原始数据转为 HTML 报告，支持 `--serve` 浏览器查看 |
| `youqu doctor` | 检查并自动修复环境依赖（pydantic、pyatspi、Java、AT-SPI、辅助功能等） |
| `youqu inspect <app_path>` | 监控应用 AT-SPI 无障碍事件，输出 NDJSON 格式数据 |
| `youqu index --rebuild` | 重建 YAML 用例索引，按模块/标签查询用例列表 |
| `youqu make <name>` | 生成 `autotest/` 脚手架（支持 YAML / Python / both） |

---

## 开发者指南

### 编译安装

从源码构建和安装：

```shell
$ git clone https://github.com/linuxdeepin/youqu.git
$ cd youqu
$ python3 -m build
$ pip3 install dist/youqu_framework-*.whl
```

> 需要 `python3 -m pip install build` 安装构建工具。

### 开发环境

使用开发模式部署，直接 pip 安装依赖（不使用虚拟环境）：

```shell
$ bash env.sh -D
```

### 代码检查

```shell
$ ruff check .     # lint
$ ruff format .    # format
$ src/utils/pylint.sh apps/autotest_xxx   # pylint HTML 报告
```

### 单元测试

```shell
$ python -m pytest -c pytest-tests.ini tests/
```

### 贡献

[贡献文档](https://youqu.uniontech.com/CONTRIBUTING.html)

---

## 开源许可证

YouQu 在 [GPL-2.0](https://github.com/linuxdeepin/youqu/blob/master/LICENSE) 下发布。
