---
name: youqu-case-generator
version: "0.3.0"
description: >
  Generate YouQu test cases in YAML (primary) or Python (fallback) from xlsx/csv or
  feature descriptions. Use whenever: YAML用例生成, xlsx转py用例, csv转py用例,
  生成YouQu用例, generate YouQu tests, 批量生成测试用例, youqu make, 创建autotest,
  AT-SPI用例生成.
---

# YouQu Case Generator

Generate complete, executable YouQu test cases in YAML (primary) or Python (fallback)
from xlsx/csv test case documents. Core principle: LLM understands test intent +
youqu-mcp provides the real AT-SPI element tree → produces genuine operations,
not trivial stubs.

## Two Operating Modes

- **xlsx/csv-driven**: Full regression suite from structured spreadsheet (id, title,
  module, precondition, steps, expected, priority).
- **feature-driven**: New feature cases from PR description, issue, requirement doc,
  or code diff. Extract testable scenarios manually, then generate.

## YAML First, Python Second

The framework now supports YAML test cases as the **primary** format for AI automation.
YAML is simpler for LLMs to generate, has built-in app lifecycle (setup/teardown),
wait_for conditions, and declarative assertions.

**When to use YAML**: Linear workflows, data-driven tests, regression suites,
AI-generated cases from xlsx/PR/issue.

**When to use Python**: Complex branching logic, custom assertions, unusual app interactions
that don't fit the declarative model.

YAML and Python cases coexist — `youqu run` collects both formats automatically.

## Non-Automatable Case Handling

Every source case produces a test method inside a batch Python file. Cases from
the same module are grouped into batches of ≤10 cases, each batch becomes one
Python test file. Non-automatable cases get `@pytest.mark.skip` — never omitted
silently.

**Automatic classification** (see `@references/skip-classification.md` for full rules):

| Category | Detection Pattern | Skip Reason |
|----------|------------------|-------------|
| Touch/gesture | 触摸, touch, 手势, pinch, swipe | skip-触摸操作无法自动化 |
| Performance | 性能, performance, 压测, 压力, 并发 | skip-性能压测类不支持自动化 |
| Hardware dependency | 需要特定硬件, 需要外设, 需要U盘, 需要打印机 | skip-依赖特定硬件环境 |
| Linglong | 玲珑, linglong | skip-玲珑环境不支持自动化 |
| System reboot | 重启, reboot, 重启后, 重启系统 | skip-重启类场景需要letmego支持 |
| External app | 调用外部应用, 打开第三方 | skip-外部应用交互无法验证 |
| Manual verification | 人工确认, 肉眼观察, 主观判断, 听感 | skip-需要人工主观判断 |

**Flag for manual review**: 多机/协同/投屏, 网络/在线, 渲染/GPU/显卡.

---

## Execution Steps

### Step 1: Parse Source Data

**xlsx/csv mode**: Use the export script to produce JSON batches:

```bash
python3 @scripts/export_xlsx.py <xlsx_or_csv_path> <output_dir> --batch-size 10
```

Each batch is a JSON file containing ≤10 cases with fields: id, title, module,
precondition, steps, expected, priority, case_type.

**feature mode**: Gather context manually from PR descriptions, git diffs, etc.

**Output format decision**: By default, generate YAML cases. Generate Python only when:
- Case requires loops, conditionals, or complex state management
- Custom assertions not covered by YAML assert types
- User explicitly requests Python format

### Step 2: Create YouQu Project Skeleton

Generate a standalone `autotest/` skeleton with the new CLI:

```bash
youqu make <name>
```

This creates an `autotest/` directory in the current working directory with
standard PO structure:

```
autotest/
├── widget/
│   ├── __init__.py          # exports <Name>Widget
│   ├── base_widget.py       # extends Src
│   ├── <name>_widget.py     # main widget class
│   ├── ui.ini               # ButtonCenter coordinates
│   └── pic_res/             # image templates
├── case/
│   ├── __init__.py          # exports BaseCase
│   ├── base_case.py         # extends AssertCommon
│   └── test_<name>_001.py   # sample test
├── conftest.py              # app-specific fixtures
├── pytest.ini               # pytest configuration
├── config.ini               # app configuration
├── report/                  # test reports output
└── yaml/
    └── test_<name>_001.yaml   # sample YAML test
```

**Naming**: `youqu make terminal` creates `autotest/` with:
- `BaseCase.APP_NAME = "terminal"`
- `BaseWidget.APP_NAME = "terminal"`
- `BaseWidget.DESC = "/usr/bin/terminal"`
- Widget class: `TerminalWidget`
- Sample test: `TestTerminal.test_terminal_001`

**Note**: `youqu make` now generates both `case/` (Python) and `yaml/` (YAML) directories.

**Customize `DESC`** in `base_widget.py` if the binary path differs
(e.g. `/usr/bin/deepin-terminal`).

### Step 3: Acquire Live AT-SPI Tree

Launch the target app and capture its accessibility tree. This reveals real element
names and structure — without it, generated code would guess at selectors.

**Full procedure**: See `@references/atspi-tree-acquisition.md`.

**Key points:**
- Set environment: `DISPLAY`, `AT_SPI_BUS_ADDRESS`, `QT_ACCESSIBILITY`
- Verify via `window_focus` and `window_get_info`
- Pass `config_path="autotest/widget/ui.ini"` to `window_*` tools if ui.ini exists
- Primary: `atspi_find_element` / `atspi_get_children_text` / `screenshot_save`
- Interactive: `atspi_find_and_click` / `atspi_find_and_right_click` (trigger menus, dialogs)
- Status: `window_get_count` / `system_get_process_status`
- Fallback: pyatspi script (see reference doc) for DTK apps with internal class names
- Capture each UI state separately (main window, menu, dialogs, search, etc.)
- Save to `autotest/docs/at-spi-tree.md`

### Step 4: Classify and Batch

1. Run automatic skip classification rules on each case
2. Flag ambiguous cases for manual review
3. Group automatable cases into batches of ≤10

### Step 5: Generate Widget Methods (Per Module)

For each module with automatable cases, generate a Widget file:

```python
from autotest.widget.base_widget import BaseWidget
from src import log

@log
class <Module>Widget(BaseWidget):

    def click_xxx_by_attr(self):
        self.dog.find_element_by_attr("Btn_xxx").click()

    def get_xxx_text(self):
        return self.dog.find_element_by_attr("Label_xxx").text
```

**Positioning strategy priority:**
1. **AT-SPI attribute** — preferred, when `atspi_find_element` succeeds
2. **OCR** — fallback for elements without AT-SPI attributes
3. **ButtonCenter (ui.ini)** — for fixed-layout elements
4. **Image recognition** — last resort, maintenance-heavy
5. **VLM (vlm_click)** — AI vision fallback when all above fail (requires VLM API)

**Method naming**: `click_<target>_by_<strategy>()`, `get_<target>_<prop>()`,
`input_<target>()`, `switch_<target>()`, `select_<target>()`, `wait_<target>()`.

See `@references/youqu-po-pattern.md` for full naming conventions and available
Src/AssertCommon methods.

### Step 6: Generate Test Case Files

For automatable cases:

```python
from autotest.case.base_case import BaseCase
from autotest.widget.<module>_widget import <Module>Widget

class Test<CaseName>(BaseCase):

    def test_<case_name>_<nnn>(self):
        """<case title>"""
        widget = <Module>Widget()
        # Step 1: <description>
        widget.<method>()
        # Assert: <expected>
        self.assert_true(...)
```

For non-automatable cases:

```python
import pytest
from autotest.case.base_case import BaseCase

class Test<CaseName>(BaseCase):

    @pytest.mark.skip(reason="<skip reason>")
    def test_<case_name>_<nnn>(self):
        """<case title> — NON-AUTOMATABLE: <reason>"""
        pass
```

**Critical naming rules** (framework enforces at collection, `conftest.py:287-304`):
- File: `test_<name>_<nnn>.py` — `<nnn>` = 3-digit padded ID
- Method: `test_<name>_<nnn>` — **must match file name exactly**
- Consequences of mismatch:
  - File/method ID differ → **skipped** (error logged)
  - File/method name part differ → **removed from collection** (silent)
  - No ID match (`test_something` without `_\d+`) → **skipped** (error logged)

### Step 7: Verify

```bash
cd autotest && youqu run --collect-only
```

Check:
- Python method count == source case count (1:1 content fidelity)
- File name ID == method name ID for every case
- All imports resolve
- Widget extends BaseWidget, TestCase extends BaseCase
- Non-automatable cases have `@pytest.mark.skip`

### Step 8: Generate YAML Test Cases (Preferred)

For automatable cases, generate YAML files in `autotest/yaml/`:

```yaml
name: "测试用例标题"
app: "app-name"
screenshot: false
vars:
  KEY: "value"

setup:
  - action: session_start
    command: "app-name"
    wait: 3.0

steps:
  - name: "步骤描述"
    action: element_action
    selector:
      name: "按钮名"
    do: "click"
    wait_after: 500
    wait_for:
      selector:
        role: "dialog"
      timeout: 5000
    assert:
      - type: element_visible
        selector:
          name: "确认"

  - name: "DBus 验证"
    action: dbus_get_property
    value:
      bus_type: "session"
      dbus_name: "com.example.Interface"
      object_path: "/com/example/Object"
      interface: "com.example.Interface"
      property: "SomeProperty"
    assert:
      - type: dbus_property
        value:
          expected: "expected_value"

teardown:
  - action: session_stop
```

**YAML Action Reference**:

| Action | Key Parameters | Description |
|--------|---------------|-------------|
| `session_start` | `command`, `wait` | Launch app process |
| `session_stop` | — | Kill app process |
| `keyboard_press` | `keys` | Single key or combo (e.g. "Return", "ctrl+a") |
| `keyboard_hot_key` | `keys` | Key combination (e.g. "ctrl,c") |
| `keyboard_type` | `text` | Type text string |
| `mouse_click` | `x`, `y` | Left click at coordinates |
| `mouse_right_click` | `x`, `y` | Right click at coordinates |
| `mouse_double_click` | `x`, `y` | Double click at coordinates |
| `mouse_scroll` | `amount` | Scroll (positive=up) |
| `mouse_drag` | `x`, `y` | Drag to coordinates |
| `element_action` | `selector`, `do` | AT-SPI element operation (do: click/right_click/double_click) |
| `element_set_value` | `selector`, `text` | Set text value on element |
| `main_menu_comb` | `items` | Keyboard-navigate main menu (e.g. ["文件", "打开"]) |
| `context_menu_comb` | `x`, `y`, `items` | Right-click + keyboard-navigate context menu |
| `dbus_call` | `value` | Call D-Bus method (value: {bus_type, dbus_name, object_path, interface, method, args}) |
| `dbus_get_property` | `value` | Read D-Bus property (value: {bus_type, dbus_name, object_path, interface, property}) |
| `wait` | `wait` | Sleep in seconds |
| `screenshot` | — | Capture screen |

**YAML Assert Reference**:

| Assert Type | Key Parameters | Description |
|-------------|---------------|-------------|
| `element_visible` | `selector` | Element exists in AT-SPI tree |
| `element_not_visible` | `selector` | Element does NOT exist |
| `element_numbers` | `selector`, `number` | Exact count of matching elements |
| `element_text` | `selector`, `expected` | Element text matches expected |
| `process_running` | `app` | Process is running |
| `process_not_running` | `app` | Process is NOT running |
| `file_exists` | `path` | File exists on disk |
| `file_not_exists` | `path` | File does NOT exist |
| `image_exist` | `path` | Template image matches screen |
| `image_not_exist` | `path` | Template image NOT on screen |
| `ocr_exist` | `text` | OCR text exists on screen |
| `ocr_not_exist` | `text` | OCR text NOT on screen |
| `window_size` | `expected`, `actual` | Window dimensions match |
| `dbus_property` | `value` | D-Bus property equals expected |

**Selector format**: Selector can be:
- `{name: "控件名"}` — match by accessible name
- `{role: "push button"}` — match by AT-SPI role
- `{name: "确定", role: "push button"}` — match by both
- `{index: 0}` — nth match

**Variable substitution**: Use `${VAR_NAME}` in any string field. Variables are defined in the top-level `vars:` section and substituted at parse time.

```yaml
vars:
  PDF_PATH: "/home/user/test.pdf"
setup:
  - action: session_start
    command: "deepin-reader ${PDF_PATH}"
```

**Wait conditions**: Steps can have `wait_for` to poll until an element appears before executing:

```yaml
- action: element_action
  selector: {name: "OK"}
  wait_for:
    selector: {role: "dialog"}
    timeout: 5000
    interval: 200
```

**Naming**: YAML files follow the same naming convention as Python: `test_<name>_<nnn>.yaml`. The name in the YAML frontmatter must match the file name.

**Non-automatable cases**: In YAML, non-automatable cases are documented with a comment header explaining the reason. The YAML itself can be a minimal stub:

```yaml
# NON-AUTOMATABLE: 触摸操作无法自动化
name: "手势缩放测试"
app: "app"
setup: []
steps: []
teardown: []
```

### Step 9: Verify

```bash
cd autotest && youqu run --collect-only
```

Check:
- Python: method count == source case count (1:1 content fidelity)
- YAML: file count == automatable case count
- Both YAML and Python cases appear in collection output
- YAML files parse without YAML errors
- Non-automatable YAML cases are documented with reason comments
- File name ID == method name ID for every Python case
- All imports resolve
- Widget extends BaseWidget, TestCase extends BaseCase
- Non-automatable Python cases have `@pytest.mark.skip`

---

## Delegation Pattern

For multi-module generation, dispatch one sub-agent per batch in parallel.

**Sub-agent prompt template:**

```
1. TASK: Generate YAML test cases (preferred) or Python test files for module "<module>" (<count> cases).
   Read JSON batch at <batch_json_path>.
   Target app: <app_name>. Working dir: <project_root>.

2. EXPECTED OUTCOME:
   - YAML files in autotest/yaml/ (preferred, for automatable cases)
   - Python files in autotest/case/ (fallback, for complex cases)
   - <count> YAML or Python files total
   - 1 Widget file in autotest/widget/<module>_widget.py
   - YAML naming: test_<name>_<nnn>.yaml (<nnn>=3-digit padded batch position)
   - Python naming: test_<name>_<nnn>.py
   - Non-automatable: YAML stub with reason comment or @pytest.mark.skip + pass body

3. REQUIRED TOOLS: read, write, edit

4. MUST DO:
   - Generate YAML by default; use Python only for complex branching/loops
   - YAML must follow schema: name, app, setup, steps, teardown
   - Each YAML step must have a meaningful action (never empty pass)
   - Read the JSON batch file for case data
   - Read existing base_widget.py and base_case.py for inheritance reference
   - Read autotest/docs/at-spi-tree.md for real element names
   - Use MCP tools for AT-SPI tree acquisition and verification (see tool list below)
   - If atspi_find_element fails, use pyatspi fallback (see @references/atspi-tree-acquisition.md)
   - Map operations to concrete Widget methods using real AT-SPI element names
   - Follow naming: file ID == method ID
   - Non-automatable → YAML stub with comment or @pytest.mark.skip(reason="..."), never omit
   - **Generated Python code MUST use YouQu framework API (Src/DogtailUtils/ButtonCenter),
     NOT MCP tool calls.** MCP tools are for the agent's exploration workflow only.

5. MUST NOT DO:
   - Modify framework source (src/, setting/, conftest.py)
   - Modify files outside autotest/
   - Invent element names without MCP verification
   - Generate "pass" stubs for automatable cases
   - Hardcode absolute paths

6. CONTEXT:
   - PO inheritance: Src → BaseWidget → <Module>Widget, AssertCommon → BaseCase → Test
   - Skip classification rules: @references/skip-classification.md
   - Assertion/Src methods: @references/youqu-po-pattern.md
   - MCP tools: @references/mcp-tool-reference.md
   - Pitfalls: @references/pitfalls.md
```

---

## Pitfalls

See `@references/pitfalls.md` for the complete list. Critical ones:

1. **Sub-agents must not modify framework source.** Explicitly forbid in every prompt.
2. **AT-SPI selectors must match reality.** Never invent names — use MCP verification.
   DTK apps often use internal class names (e.g., `DTitlebarDWindowOptionButton`).
3. **File name ID must match method name ID.** Mismatch → silently skipped.
4. **Every source case needs a file.** Non-automatable → `@pytest.mark.skip`, never omit.
5. **Widget methods: one thing each.** Don't combine operations — defeats PO composability.
6. **YAML is preferred over Python for AI automation.** LLMs generate more correct
   YAML than Python. Use Python only for complex branching.
7. **YAML action/assert names must match the reference table.** Unknown types cause
   runtime errors. See Step 8 reference tables for supported types.
8. **YAML selector format**: Use `{name: "text"}` with curly braces (dict), NOT
   AT-SPI expr syntax `$/name/`. The executor converts selectors to AT-SPI expr internally.
9. **Wait conditions**: Always add `wait_for` before steps that depend on UI state
   changes (dialog opens, page loads, etc.). Set reasonable timeouts (3000-10000ms).

---

## Reference Files

| File | Purpose |
|------|---------|
| `@references/youqu-po-pattern.md` | Inheritance chain, Src methods, assertions, Widget conventions |
| `@references/mcp-tool-reference.md` | MCP tool reference with parameters and usage |
| `@references/skip-classification.md` | Full skip rules with detection patterns |
| `@references/atspi-tree-acquisition.md` | AT-SPI tree capture procedure (env, launch, dump, persist) |
| `@references/pitfalls.md` | Complete pitfalls list with root causes |
| `@references/yaml-schema.md` (NEW) | YAML schema reference with all actions, asserts, and selectors |
| `@scripts/export_xlsx.py` | Batch export xlsx/csv rows to JSON |
| `@assets/widget_template.py` | Widget file template with common method patterns |
| `@assets/case_template.py` | Test case file template |
