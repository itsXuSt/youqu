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

## [YouQu（有趣）能做什么]()

- [X]  💻 Linux 桌面应用 UI 自动化测试
- [X]  🌏 Web UI 自动化测试
- [X]  🚌 Linux DBus 接口自动化测试
- [X]  🚀 命令行自动化测试
- [X]  🕷️ HTTP 接口自动化测试

## [安装]()

从 PyPI 安装:

```shell
$ sudo pip3 install youqu-framework
```

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

## [创建项目]()

您可以在任意目录下，使用 `youqu-startproject` 命令创建一个项目：

```shell
$ youqu-startproject my_project
```

注意：所有命令不要以 `root` 用户执行！

如果 `youqu-startproject` 后面不加参数，默认的项目名称为：`youqu` ；

![](./docs/assets/install.gif)

## [安装依赖]()

安装部署 YouQu 执行所需环境：

```shell
$ cd my_project
$ bash env.sh
# 使用的默认密码是 1；
# 您可以使用 -p 选项传入密码：bash env.sh -p ${my_password}；
# 也可以修改配置文件 setting/globalconfig.ini 里面的 PASSWORD 配置项；
```

## [创建 APP 工程]()

使用 `startapp` 命令自动创建 APP 工程：

```shell
$ youqu manage.py startapp autotest_deepin_some
```

自动创建的 APP 工程遵循完整的 PO 设计模式，让你可以专注于用例和方法的编写维护。

在 `apps` 目录下会自动创建一个 APP 工程：`autotest_deepin_some`，同时新建好工程模板目录和模板文件：

```shell
my_project
├── apps
│   ├── autotest_deepin_some  # <-- APP工程
...     ├── ...
```

**在你的远程 Git 仓库中，只需要保存 APP 工程这部分代码即可。**

`autotest_deepin_some` 是你的  APP 工程名称，在此基础上，你可以快速的开始你的 AT 项目，更重要的是确保创建工程的规范性。

`apps` 目录下可以存在任意多个 APP 工程。

[运行]()
--------

### [1. 执行管理器]()

在项目根目录下有一个 `manage.py` ，它是一个执行器入口，提供了本地执行、远程执行等的功能。

### [2. 本地执行]()

```shell
$ youqu manage.py run
```

#### [2.1. 命令行参数]()

在一些 CI 环境下使用命令行参数会更加方便：

```shell
$ youqu manage.py run -a apps/autotest_deepin_some -k "xxx" -t "yyy"
```

更多用法可以使用 `-h` 或 `--help` 查看。

#### [2.2. 配置文件]()

通过配置文件配置参数

在配置文件 [setting/globalconfig.ini](https://github.com/linuxdeepin/youqu/blob/master/setting/globalconfig.ini)  里面支持配置对执行的一些参数进行配置。

### [3. 远程执行]()

远程执行就是用本地作为服务端控制远程机器执行，远程机器执行的用例相同。

使用 `remote` 命令：

```shell
$ youqu manage.py remote
```

## [MCP Server — AI 驱动的桌面自动化]()

YouQu 内置 MCP (Model Context Protocol) Server，将桌面 UI 自动化能力暴露为 MCP 工具，
使 AI 客户端（Claude、OpenCode 等）能够直接操控测试机上的桌面应用。

### 功能概览

| 工具组 | 能力 | 示例 |
|--------|------|------|
| **AT-SPI 操作** | 元素查找、点击、输入、滚动、悬停 | 点击按钮、输入文本、展开菜单 |
| **键盘鼠标** | 按键、快捷键、点击、移动 | Enter、Ctrl+C、鼠标左键 |
| **窗口管理** | 窗口列表、激活、关闭、最大化/最小化 | 切换窗口、关闭弹窗 |
| **截图** | 全屏截图并保存 | 保存当前屏幕到证据目录 |
| **进程管理** | 查询进程、终止进程（保护关键进程） | 关闭应用进程 |
| **系统命令** | 执行只读命令（ps、gsettings 等） | 查询系统设置 |
| **VLM 视觉** | 视觉定位元素、视觉断言、自主测试 | "点击桌面左下角的终端图标" |

### 安装依赖

MCP Server 为可选功能，需要 Python >= 3.10：

```shell
pip install youqu-framework[mcp]
```

### VLM 配置

编辑 `setting/globalconfig.ini`，启用 VLM 并配置后端 API：

```ini
[vlm]
VLM_ENABLED = true
VLM_BASE_URL = https://api-inference.modelscope.cn/v1/
VLM_MODEL = Qwen/Qwen3-VL-8B-Instruct
VLM_API_KEY = your-api-key
```

VLM 需要 OpenAI 兼容的视觉语言模型 API（Ollama、ModelScope、vLLM 等），框架不内置模型。

### 启动 MCP Server

#### stdio 模式（本地子进程）

```shell
youqu manage.py mcp
```

适用于本地 AI 客户端通过 stdio 管道连接。

#### Streamable HTTP 模式（远程连接）

在测试机上启动 HTTP 服务：

```shell
youqu manage.py mcp --transport http --host 0.0.0.0 --port 8000
```

CLI 参数说明：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--transport` | `stdio` | `stdio`（本地子进程）/ `sse`（HTTP+SSE）/ `http`（Streamable HTTP，推荐远程） |
| `--host` | `127.0.0.1` | 监听地址，远程连接需设为 `0.0.0.0` |
| `--port` | `8000` | 监听端口 |

### 客户端连接配置

#### Claude（原生支持 HTTP）

```bash
claude mcp add --transport http youqu http://192.168.1.100:8000/mcp
```

#### OpenCode

在项目 `opencode.json` 中配置 MCP server：

```json
{
  "mcp": {
    "youqu": {
      "command": "youqu",
      "args": ["manage.py", "mcp", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
    }
  }
}
```

或连接远程测试机：

```json
{
  "mcp": {
    "youqu-remote": {
      "type": "http",
      "url": "http://192.168.1.100:8000/mcp"
    }
  }
}
```

#### SSH 隧道（安全内网连接）

无需在测试机暴露端口，通过 SSH 隧道转发：

```shell
# 本地执行
ssh -L 8000:localhost:8000 user@test-machine
```

然后本地客户端连接 `http://127.0.0.1:8000/mcp`。

### 客户端兼容矩阵

| AI 客户端 | stdio | Streamable HTTP |
|-----------|:-----:|:---------------:|
| Claude | ✅ | ✅ |
| OpenCode | ✅ | ✅ |

## [贡献]()

[贡献文档](https://youqu.uniontech.com/CONTRIBUTING.html)

## [开源许可证]()

YouQu 在 [GPL-2.0](https://github.com/linuxdeepin/youqu/blob/master/LICENSE) 下发布。
