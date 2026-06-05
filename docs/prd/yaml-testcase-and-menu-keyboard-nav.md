# PRD: YAML 用例 pytest 集成 + 键盘导航菜单模块

> 版本: 1.0
> 日期: 2026-06-05
> 状态: 已确认

## 1. 背景与目标

### 1.1 问题

1. **LLM 生成的 py 用例质量参差不齐** — LLM 不熟悉 AT-SPI expr 语法，sleep 时间靠猜，右键菜单操作写法混乱。`youqu make` 骨架的 conftest.py 为空，无 app lifecycle fixture；框架无 `wait_until` API；`DogtailUtils` 右键仅有 `element_click(element, button=3)`，无菜单项选择。
2. **菜单操作不稳定** — DTK 的 `DMenu::exec()` 创建的 transient popup 不在静态 AT-SPI 树中。当前 `deepin-mcp` 用 hover-crawl（鼠标 6-12px 步长向下移动 + AT-SPI focus 事件监听），鼠标偏移导致选不上，代码 483 行。Reader 右键测试约 40% 标记 xfail。
3. **py 用例执行效率低** — 每次 `DogtailUtils()` 构造都调用 `root.application()`，无 session 缓存；操作间硬编码 `sleep(0.3-1.0)`；无条件等待机制。
4. **跨 app 重复工作** — `BaseWidget`、`config.ini`、窗口操作方法在每个 app 工程中 100% 重复，仅 `APP_NAME`/`DESC` 不同。

### 1.2 目标

1. 键盘导航菜单：用 ↑↓←→Enter 方案替代 hover-crawl，更快更稳定，py 用例和 YAML 用例都能用。
2. YAML 作为首选用例格式：AI 自动化用 YAML，复杂场景用 py 补充。
3. YAML 通过 pytest 执行：复用 YouQu 全部断言（AssertCommon 22 种）、报告（Allure）、键鼠 API（MouseKey + Wayland 支持）。
4. YAML action/assert 可扩展：不限于初始映射，后续按需新增。
5. 不实现 CSV 标签和 PMS 集成（AI 自动化不需要）。

### 1.3 不做的事

- 不改造现有 `manage.py` / `LocalRunner` / `RemoteRunner`。
- 不改造根 `conftest.py` 的 CSV/PMS 逻辑。
- 不移植 deepin-mcp 的独立 runner（改用 pytest 集成）。
- 不移植 deepin-mcp 的 `input_controller.py` / `element_actor.py` / `tree_walker.py`（YouQu 已有等价实现）。
- 不修改现有 py 用例的执行方式。
- 不修改 `src/__init__.py` 的多继承链。

## 2. 架构设计

### 2.1 YAML 用例执行流

```
youqu run
  → pytest plugin 加载 (sys.path + env)
  → pytest_collect_file hook 收集 .yaml 文件
  → YamlFile(path) → 解析 YAML → 生成 YamlItem
  → YamlItem.runtest():
      execute_setup (session_start)
      FOR EACH step:
          wait_for (条件等待, 可选)
          execute_step (action → YouQu API 调用)
          check_assertions (assert → AssertCommon 方法)
          wait_after (步骤后等待)
      execute_teardown (session_stop)
  → 自动获得 Allure 报告 / pytest markers / reruns / parallel
```

### 2.2 键盘导航菜单方案

```
菜单操作流:
  1. 打开菜单 (Alt 键 / 右键坐标)
  2. 键盘 ↑↓ 导航到目标项 (DTK 菜单原生支持)
  3. 如有子菜单: → 进入子菜单, ← 返回父菜单
  4. Enter 确认选择
  5. Escape 关闭菜单

对比:
  hover-crawl: 鼠标逐像素移动 + 事件监听, ~483 行, 不稳定
  键盘导航: ↑↓←→Enter + AT-SPI focused state 读取, ~150 行, 稳定
```

### 2.3 新增文件结构

```
youqu/
├── src/
│   └── menu_nav.py              # [新增] 键盘导航菜单模块
├── src/yaml_test/               # [新增] YAML 测试执行引擎
│   ├── __init__.py
│   ├── collector.py             # pytest collect hook
│   ├── parser.py                # YAML 解析 (Pydantic models + 变量替换)
│   ├── executor.py              # step action 分发到 YouQu API
│   ├── assertions.py            # YAML assert → AssertCommon 映射
│   └── wait.py                  # wait_for 条件等待
└── cli/make.py                  # [修改] 骨架新增 yaml/ 目录
```

| 文件 | 职责 | 行数 (估计) |
|------|------|------------|
| `src/menu_nav.py` | 键盘导航菜单操作器 | ~150 |
| `src/yaml_test/collector.py` | pytest collect hook + YamlFile + YamlItem | ~80 |
| `src/yaml_test/parser.py` | YAML schema 解析 + 变量替换 | ~120 |
| `src/yaml_test/executor.py` | step action 分发 + selector 转换 | ~200 |
| `src/yaml_test/assertions.py` | assert type → AssertCommon 映射 | ~100 |
| `src/yaml_test/wait.py` | AT-SPI 条件等待 | ~40 |

## 3. 详细设计

### 3.1 键盘导航菜单模块 (`src/menu_nav.py`)

```python
import time
from src.dogtail_utils import DogtailUtils
from src.mouse_key import MouseKey


class MenuNotFoundError(Exception):
    """菜单项未找到"""
    pass


class MenuNavigator:
    """键盘导航菜单操作器, 基于 ↑↓←→Enter 方案。
    DTK 菜单 (DMenu::exec()) 创建 transient popup, 不在静态 AT-SPI 树中。
    本模块用键盘导航 + AT-SPI focused state 读取, 稳定可靠。
    """

    MAX_LOOP = 50  # 单层菜单最大循环次数 (防无限循环)

    def __init__(self, name: str = None, desc: str = None):
        self.app_name = name
        self.desc = desc
        self.mk = MouseKey()
        self._app_node = None  # 缓存 AT-SPI 应用节点, 避免每次重新连接

    def _ensure_app_node(self):
        """懒加载 AT-SPI 应用节点, 整个导航过程中复用"""
        if self._app_node is None:
            dog = DogtailUtils(self.app_name, self.desc) if self.app_name else DogtailUtils()
            self._app_node = dog.obj  # DogtailUtils.obj 是已连接的 app 节点
        return self._app_node

    def open_main_menu(self) -> None:
        """通过 Alt 键打开主菜单栏"""
        self.mk.press_key("Alt")
        time.sleep(0.3)

    def open_context_menu(self, x: int, y: int) -> None:
        """在指定坐标右键打开上下文菜单"""
        self.mk.right_click(x, y)
        time.sleep(0.3)

    def _read_focused_item(self) -> str:
        """读取当前 AT-SPI focused 状态的菜单项文本。
        递归遍历 AT-SPI 树, 查找 states 包含 'focused' 的 menu item 节点。
        复用 _app_node 缓存, 避免每次重新 AT-SPI 连接。
        """
        app_node = self._ensure_app_node()
        for child in self._walk_menu_items(app_node):
            if child is None:
                continue
            states = set(
                s.lower() for s in getattr(child, "states", [])
                if hasattr(child, "states")
            )
            if "focused" in states:
                return getattr(child, "name", "") or ""
        return ""

    def _walk_menu_items(self, node):
        """递归遍历 AT-SPI 树中的 menu/menu_item 节点"""
        try:
            children = node.children if hasattr(node, "children") else []
        except Exception:
            return
        for child in children:
            try:
                role = getattr(child, "roleName", "").lower()
            except Exception:
                continue
            if role in ("menu item", "menu", "check menu item",
                        "radio menu item", "push button"):
                yield child
            yield from self._walk_menu_items(child)

    def navigate_to(self, items: list, exact: bool = False) -> None:
        """导航到目标菜单项。
        Args:
            items: 菜单路径, 如 ["文件", "打开"] 或 ["复制"]
            exact: True=精确匹配, False=子串匹配
        Raises:
            MenuNotFoundError: 目标项未找到
        """
        for i, target in enumerate(items):
            found = False
            start_text = self._read_focused_item()
            for _ in range(self.MAX_LOOP):
                current = self._read_focused_item()
                if not current:
                    raise MenuNotFoundError(
                        f"菜单已关闭, 无法导航到 '{target}'"
                    )
                matched = (current == target if exact
                          else target.lower() in current.lower())
                if matched:
                    found = True
                    break
                if current == start_text and _ > 0:
                    raise MenuNotFoundError(
                        f"菜单项 '{target}' 不存在于第 {i+1} 层菜单"
                    )
                self.mk.press_key("Down")
                time.sleep(0.1)
            if not found:
                raise MenuNotFoundError(
                    f"菜单项 '{target}' 未找到 (超过 {self.MAX_LOOP} 次)"
                )
            if i < len(items) - 1:
                self.mk.press_key("Right")
                time.sleep(0.3)

    def select(self, items: list, exact: bool = False) -> None:
        """navigate_to + Enter 的快捷方法"""
        self.navigate_to(items, exact)
        self.mk.press_key("Return")
        time.sleep(0.3)

    def cancel(self) -> None:
        """Escape 关闭当前菜单"""
        self.mk.press_key("Escape")
```

### 3.2 pytest 收集 hook (`src/yaml_test/collector.py`)

```python
import pytest


def pytest_collect_file(parent, path):
    """pytest hook: 收集 .yaml 文件为测试项。
    仅在 pytest.ini 包含 yaml_files 配置时激活。
    """
    yaml_dirs = parent.config.getini("yaml_files")
    if not yaml_dirs:
        return None
    if path.ext == ".yaml":
        # 检查文件是否在 yaml_files 配置的目录下
        for d in yaml_dirs:
            yaml_dir = parent.config.rootdir / d
            if path.relto(yaml_dir) or path == yaml_dir:
                return YamlFile.from_parent(parent, fspath=path)
    return None


class YamlFile(pytest.File):
    """YAML 测试文件"""

    def collect(self):
        from src.yaml_test.parser import parse_testcase
        testcase = parse_testcase(self.fspath)
        yield YamlItem.from_parent(self, name=testcase.name, testcase=testcase)


class YamlItem(pytest.Item):
    """YAML 测试项, 直接 runtest 不触发根 conftest.py 的 CSV/PMS 钩子"""

    def __init__(self, name, parent, testcase):
        super().__init__(name, parent)
        self.testcase = testcase

    def runtest(self):
        from src.yaml_test.executor import StepExecutor
        result = StepExecutor(self.testcase).run()
        if not result.passed:
            raise YamlTestError(result.message)

    def repr_failure(self, excinfo):
        if isinstance(excinfo.value, YamlTestError):
            return str(excinfo.value)
        return super().repr_failure(excinfo)

    def reportinfo(self):
        return self.fspath, 0, self.testcase.name


class YamlTestError(Exception):
    """YAML 用例执行失败"""
    pass
```

### 3.3 YAML Schema (`src/yaml_test/parser.py`)

**核心 YAML 格式**:

```yaml
name: "用例标题"                # 必填, pytest 用例名
app: "deepin-reader"            # 必填, 进程名
screenshot: true                 # 可选, 每步截图 (默认 false)
vars:                            # 可选, ${VAR} 替换
  PDF_PATH: "/path/to/file.pdf"
setup:                           # 必填
  - action: session_start
    command: "deepin-reader ${PDF_PATH}"
    wait: 3.0
steps:                           # 必填
  - name: "打开文件菜单"
    action: main_menu_comb
    items: ["文件", "打开"]
    wait_after: 500              # 毫秒
  - name: "点击确定按钮"
    action: element_action
    selector: {name: "确定"}
    do: click
    wait_for:                    # 可选, 步前条件等待
      selector: {role: "dialog"}
      timeout: 5000
    assert:
      - type: element_visible
        selector: {name: "OK"}
teardown:                         # 必填
  - action: session_stop
```

**Pydantic 模型** — `TestCase(name, app, screenshot, vars, setup, steps, teardown)`，其中 `ActionStep(action, name, selector, do, items, command, wait, wait_after, wait_for, x, y, amount, keys, text, assert)`，`Selector(name, role, accessible_id, index)`，`AssertStep(type, selector, expected, value, app, path)`。变量替换: 解析前遍历所有字符串字段, 将 `${VAR}` 替换为 `vars` 中定义的值。

### 3.4 Step Executor (`src/yaml_test/executor.py`)

**selector → AT-SPI expr 转换**:

```python
def selector_to_expr(selector: dict) -> str:
    """{name: "打开", role: "push button"} → "//push button[name=打开]"
    {accessible_id: "btn_ok"}        → "//*[@accessible_id=btn_ok]"
    {name: "确定"}                   → "确定"
    """
    role = selector.get("role", "")
    name = selector.get("name", "")
    aid = selector.get("accessible_id", "")
    if role and name:
        return f"//{role}[name={name}]"
    if role:
        return f"//{role}"
    if name:
        return name
    if aid:
        return f"//*[@accessible_id={aid}]"
    return ""
```

**Action 映射表 (18 种)**:

| YAML action | YouQu API | 说明 |
|-------------|-----------|------|
| `session_start` | `subprocess.Popen(cmd)` + DogtailUtils | 启动应用 |
| `session_stop` | `pkill -f {app}` | 停止应用 |
| `keyboard_press` | `MouseKey.press_key(keys)` | 单键 |
| `keyboard_hot_key` | `MouseKey.hot_key(*keys.split(","))` | 组合键 |
| `keyboard_type` | `MouseKey.input_message(text)` | 输入文本 |
| `mouse_click` | `MouseKey.click(x, y)` | 坐标点击 |
| `mouse_right_click` | `MouseKey.right_click(x, y)` | 坐标右键 |
| `mouse_double_click` | `MouseKey.double_click(x, y)` | 坐标双击 |
| `mouse_scroll` | `MouseKey.mouse_scroll(amount)` | 滚轮 |
| `mouse_drag` | `MouseKey.drag_to(x, y)` | 拖拽 |
| `element_action` | `DogtailUtils.find_element_by_attr(expr)` + do | AT-SPI 元素操作 |
| `element_set_value` | find_element + click + input_message | 设置控件值 |
| `main_menu_comb` | `MenuNavigator.open_main_menu()` + select(items) | 主菜单导航 |
| `context_menu_comb` | `MenuNavigator.open_context_menu(x,y)` + select(items) | 右键菜单导航 |
| `dbus_call` | `DbusUtils.session/system_object_methods()` | D-Bus 方法调用 |
| `dbus_get_property` | `DbusUtils.get_session/system_properties_value()` | D-Bus 属性读取 |
| `wait` | `time.sleep(ms/1000)` | 显式等待 |
| `screenshot` | `ImageCenter.save_temporary_picture(0,0,W,H)` | 全屏截图 |

**Assert 映射表 (15 种)**:

| YAML assert type | AssertCommon 方法 | 说明 |
|------------------|-------------------|------|
| `element_visible` | `assert_element_exist(expr)` | 元素可见 |
| `element_not_visible` | `assert_element_not_exist(expr)` | 元素不可见 |
| `element_numbers` | `assert_element_numbers(expr, n)` | 元素数量 |
| `element_text` | 读取 element.name + assert equal | 元素文本匹配 |
| `process_running` | `assert_process_status("running", app)` | 进程运行中 |
| `process_not_running` | `assert_process_status("not_running", app)` | 进程已停止 |
| `file_exists` | `assert_file_exist(path)` | 文件存在 |
| `file_not_exists` | `assert_file_not_exist(path)` | 文件不存在 |
| `image_exist` | `assert_image_exist(path)` | 图像匹配 |
| `image_not_exist` | `assert_image_not_exist(path)` | 图像不存在 |
| `ocr_exist` | `assert_ocr_exist(text)` | OCR 文字存在 |
| `ocr_not_exist` | `assert_ocr_not_exist(text)` | OCR 文字不存在 |
| `window_size` | `assert_window_size(expect, real)` | 窗口尺寸 |
| `window_amount` | `assert_window_amount(app, n)` | 窗口数量 |
| `dbus_property` | DbusUtils.get_property() + assert | D-Bus 属性值 |

### 3.5 wait_for 条件等待 (`src/yaml_test/wait.py`)

```python
import time
from src.dogtail_utils import DogtailUtils


def wait_for(selector: dict, timeout: int = 5000,
             interval: int = 200) -> bool:
    """轮询 AT-SPI 树直到元素出现。True=找到, False=超时。"""
    from src.yaml_test.executor import selector_to_expr
    expr = selector_to_expr(selector)
    if not expr:
        return False
    deadline = time.time() + timeout / 1000
    dog = DogtailUtils()
    while time.time() < deadline:
        try:
            if dog.find_elements_by_attr(expr):
                return True
        except Exception:
            pass
        time.sleep(interval / 1000)
    return False
```

### 3.6 pytest plugin 更新 (`plugin/__init__.py`)

在现有 `pytest_configure` 末尾追加 YAML hook 注册:

```python
def pytest_configure(config):
    _inject_paths()
    _setup_env()
    yaml_dirs = config.getini("yaml_files")
    if yaml_dirs:
        config.pluginmanager.import_plugin("src.yaml_test.collector")
```

`pyproject.toml` 新增 ini option: `[tool.pytest.ini_options] yaml_files =`

### 3.7 `youqu make` 骨架更新

骨架新增 `yaml/` 目录:

```
autotest/
├── pytest.ini               # [修改] 新增 yaml_files = yaml
├── case/                    # py 用例 (不变)
├── yaml/                    # [新增] YAML 用例目录
│   └── test_example.yaml
├── widget/                  # 不变
└── report/                  # 不变
```

pytest.ini 模板: `testpaths = case` + `yaml_files = yaml`

示例 YAML 用例 (`test_example.yaml`):

```yaml
name: "示例: 打开关于对话框"
app: "deepin-reader"
setup:
  - action: session_start
    command: "deepin-reader"
    wait: 3.0
steps:
  - name: "打开主菜单"
    action: main_menu_comb
    items: ["帮助", "关于"]
  - name: "验证对话框出现"
    wait_for:
      selector: {role: "dialog"}
      timeout: 5000
    assert:
      - type: element_visible
        selector: {name: "关于"}
teardown:
  - action: session_stop
```

## 4. 兼容性

| 现有功能 | 影响 |
|----------|------|
| `youqu manage.py run` | 无影响 — 不经过新代码 |
| `youqu run` (py 用例) | 无影响 — pytest_collect_file 仅匹配 .yaml |
| `apps/` 目录结构 | 无影响 |
| CSV 标签格式 | 无影响 — YamlItem 不触发 CSV 钩子 |
| PMS 回填 | 无影响 — YamlItem 不触发 PMS 钩子 |
| `from src import Src` | 无影响 — pytest plugin 自动注入 sys.path |
| `from src.menu_nav import MenuNavigator` | py 用例可直接使用 |

## 5. 验收标准

### 5.1 键盘导航菜单

- [ ] `MenuNavigator.select(["文件", "打开"])` 能在 DTK 应用中正确导航主菜单并执行
- [ ] `MenuNavigator.select(["复制"])` 能在右键菜单中正确选择目标项
- [ ] 子菜单导航 (←→) 正常工作
- [ ] 目标项不存在时抛 `MenuNotFoundError`
- [ ] 循环保护: 不会无限循环 (回到起点自动终止)
- [ ] py 用例中可以直接 `from src.menu_nav import MenuNavigator` 使用

### 5.2 YAML pytest 集成

- [ ] `youqu run` 能收集 `yaml/` 目录下的 .yaml 文件
- [ ] YAML 用例在 Allure 报告中正常显示 (用例名、步骤、断言)
- [ ] `youqu run -k "关键词"` 能过滤 YAML 用例
- [ ] `youqu run --collect-only` 能正确列出 YAML 用例
- [ ] YAML 用例不触发 CSV/PMS 逻辑
- [ ] 18 种 action 类型全部可执行
- [ ] 15 种 assert 类型全部可验证
- [ ] `wait_for` 条件等待正常工作 (超时正确返回 False)
- [ ] `${VAR}` 变量替换正常工作

### 5.3 不退化

- [ ] 现有 py 用例执行不受影响
- [ ] 现有 `manage.py run` 流程不受影响
- [ ] 现有 CSV/PMS 流程不受影响
