---
name: youqu-case-generator
version: "0.1.0"
description: >
  Generate executable Python test case files for the YouQu framework from structured
  test case sources (xlsx/csv spreadsheets or feature descriptions). Core principle:
  LLM understands test intent + live AT-SPI tree via youqu-mcp extracts real selectors,
  producing genuine PO-pattern test code (not "start then wait then exit" stubs).
  Automatically creates complete YouQu APP project structure with Widget methods
  organized by module. Non-automatable cases (touchscreen, environment, performance,
  linglong, etc.) are marked with skip reasons rather than silently omitted.
  Output is YouQu-framework-compatible Python test files with proper PO inheritance
  chain (Src → BaseWidget → XxxWidget, AssertCommon → XxxAssert → BaseCase → TestXxx).
  Triggers: xlsx转py用例, csv转py用例, 生成YouQu用例, 从用例表生成测试代码,
  YouQu test generation, casefile to YouQu, 自动化用例生成, generate YouQu tests,
  xlsx to python test cases, 批量生成测试用例, deepin-terminal用例生成.
---

# YouQu Case Generator

Generate complete, executable YouQu Python test projects from xlsx/csv test case
documents. The core principle: LLM understands the test intent + youqu-mcp provides
the real AT-SPI element tree → produces genuine operations that exercise the app,
not trivial pass-through stubs.

## Two Operating Modes

### Mode 1: xlsx/csv-driven (Full Regression Suite)

Source: structured spreadsheet with test case design data (id, title, module,
precondition, steps, expected, priority).

### Mode 2: feature-driven (New Feature Test Cases)

Source: PR description, issue, requirement doc, or code diff.

For this mode, extract testable scenarios, navigate to the new feature in the
running app, get AT-SPI tree, then generate.

## Skip Classification: Non-Automatable Cases

Before generating code, classify each case. Cases that cannot be automated must be
**generated as Python test files with skip markers**, not omitted. This preserves
the 1:1 mapping.

### Automatic Classification Rules

| Category | Detection Pattern | Skip Reason |
|----------|------------------|-------------|
| Touch/gesture | 触摸, touch, 手势, pinch, swipe, 手势缩放, 多点触控 | skip-触摸操作无法自动化 |
| Performance | 性能, performance, 压测, 压力, 并发 | skip-性能压测类不支持自动化 |
| Environment dependency | 需要特定硬件, 需要外设, 需要U盘, 需要打印机, 需要蓝牙设备 | skip-依赖特定硬件环境 |
| Linglong | 玲珑, linglong | skip-玲珑环境不支持自动化 |
| System reboot | 重启, reboot, 重启后, 重启系统 | skip-重启类场景需要letmego支持 |
| External app | 调用外部应用, 打开第三方, 外部程序 | skip-外部应用交互无法验证 |
| Manual verification | 人工确认, 肉眼观察, 主观判断, 听感 | skip-需要人工主观判断 |

### Manual Classification (Review Required)

Some categories need human judgment. Flag for review:

- **Multi-machine interaction**: 多机, 协同, 投屏 → mark as `skip-多机交互待评估`
- **Pure network dependency**: 网络, 在线 → evaluate if mockable
- **GPU/rendering**: 渲染, GPU, 显卡 → evaluate if screenshot-verifiable

## Execution Steps

### Step 1: Parse Source Data

**xlsx/csv mode**: Use the export script to produce JSON batches:

```bash
python3 @scripts/export_xlsx.py <xlsx_or_csv_path> <output_dir> --batch-size 10
```

Each batch is a JSON file containing ≤10 cases with fields: id, title, module,
precondition, steps, expected, priority, case_type.

**feature mode**: Gather context manually from PR descriptions, git diffs, etc.

### Step 2: Auto-Create YouQu APP Project

Execute `youqu manage.py startapp` to create the PO-pattern skeleton:

```bash
youqu manage.py startapp autotest_<app_name>
```

This creates the standard structure:
```
apps/autotest_<app_name>/
├── widget/
│   ├── base_widget.py    # Base class (extends Src)
│   ├── <app>_widget.py   # Main widget export class
│   ├── other_widget.py   # Per-module widget stubs
│   ├── ui.ini            # ButtonCenter coordinate config
│   └── pic_res/          # Image template storage
├── case/
│   ├── base_case.py      # Test case base class
│   └── test_mycase_001.py
├── <app>.csv             # CSV label file
├── <app>_assert.py       # Custom assertion class
├── config.py             # Application config
├── config.ini            # App-level INI config
├── control               # Dependency version record
└── conftest.py           # pytest fixture plugin
```

Important: the `startapp` command performs template variable substitution
(`${APP_NAME}`, `${app_name}`, `${AppName}`, `${USER}`, `${DATE}`, `${TIME}`).

### Step 3: Get Live AT-SPI Tree via youqu-mcp

Launch the target app and capture its accessibility tree. This reveals real element
names, roles, and structure — without it, you're guessing at selectors.

```
# Focus/launch the app
youqu-mcp_window_focus(app_name="deepin-music")

# Get window info (position, size)
youqu-mcp_window_get_info(app_name="deepin-music")

# Find elements by AT-SPI path expression
youqu-mcp_atspi_find_element(app_name="deepin-music", expr="$/name/role")

# Get children text (for list/tree views)
youqu-mcp_atspi_get_children_text(app_name="deepin-music", element_expr="$/name/role")

# Take screenshot for visual reference
youqu-mcp_screenshot_save()
```

**Key things to extract from the tree:**
- Element names and roles (for `dog.find_element_by_attr("Btn_xxx")`)
- Menu item labels (for `dog.element_click("设置")`)
- Dialog titles and button names
- Widget hierarchy for nested navigation
- AT-SPI path expressions: `$/app_name//element_name`

**AT-SPI path expression syntax for youqu-mcp:**
- `$/app_name//element` — search under app
- `$/role` — search by role
- `$/name` — search by name
- `$/name/role` — combined search

### Step 4: Classify and Batch

Parse the exported JSON, classify each case, and split automatable cases into
batches of ≤10.

Classification priority:
1. First: run automatic rules from the table above
2. Second: flag ambiguous cases for manual review
3. Third: group remaining automatable cases into batches

Mark classified cases in a summary file for traceability.

### Step 5: Generate Widget Methods (Per Module)

For each module that has automatable cases, generate a Widget file. The file
follows the YouQu PO pattern:

```python
# widget/<module>_widget.py
from apps.autotest_<app>.widget.base_widget import BaseWidget
from src import log

@log
class <Module>Widget(BaseWidget):
    """Widget methods for the <module> functionality."""

    def click_xxx_by_attr(self):
        """Click xxx button via AT-SPI attribute."""
        self.dog.find_element_by_attr("Btn_xxx").click()

    def get_xxx_text_by_attr(self):
        """Get text of xxx element."""
        return self.dog.find_element_by_attr("Label_xxx").text

    def click_xxx_in_menu(self):
        """Click xxx via DTK menu navigation."""
        self.dog.element_click("xxx")
```

**Widget method naming conventions:**
- `click_<target>_by_attr()` — click via AT-SPI attribute
- `click_<target>_by_image()` — click via image recognition
- `click_<target>_by_ocr()` — click via OCR text recognition
- `click_<target>_by_ui()` — click via ButtonCenter (ui.ini coordinates)
- `get_<target>_<property>()` — read property (text, position, state)
- `input_<target>()` — type text into input field
- `switch_<target>()` — toggle a switch/checkbox
- `select_<target>()` — select from dropdown/list
- `wait_<target>()` — wait for element to appear
- `verify_<target>()` — verify element state without assertion

**How to choose positioning strategy:**
1. **AT-SPI attribute** — preferred. Use when `atspi_find_element` returns the element.
2. **OCR** — fallback for elements without AT-SPI attributes. Use `self.ocr("text")`.
3. **ButtonCenter (ui.ini)** — for fixed-layout elements. Requires updating `widget/ui.ini`.
4. **Image recognition** — last resort, maintenance-heavy. Use `self.find_image("pic.png")`.

### Step 6: Generate Test Case Files

For each automatable case, generate a Python test file following YouQu conventions:

```python
# case/test_<case_name>_<nnn>.py
from apps.autotest_<app>.case.base_case import BaseCase
from apps.autotest_<app>.widget.<module>_widget import <Module>Widget

class Test<CaseName>(BaseCase):

    def test_<case_name>_<nnn>(self):
        """<case title from xlsx source>"""
        widget = <Module>Widget()
        # Step 1: <step description>
        widget.<method_name>()
        # Step 2: <step description>
        result = widget.<method_name>()
        # Assert: <expected result>
        self.assert_true(result)
```

**Critical naming rules:**
- File name: `test_<case_name>_<nnn>.py` — `<nnn>` is a 3-digit ID padded from
  the original case number (e.g., case 7 → `007`, case 42 → `042`)
- Class name: `Test<CaseName>` — PascalCase
- Method name: `test_<case_name>_<nnn>` — must match file name's prefix
- File name and method name ID must be consistent (framework enforces this)

For non-automatable cases, generate files with skip decorators:

```python
# case/test_<case_name>_<nnn>.py
import pytest
from apps.autotest_<app>.case.base_case import BaseCase

class Test<CaseName>(BaseCase):

    @pytest.mark.skip(reason="<skip reason>")
    def test_<case_name>_<nnn>(self):
        """<case title> — NON-AUTOMATABLE: <reason>"""
        pass
```

### Step 7: Verify Generated Files

After generation, verify:
1. **File count**: Python test file count == source case count (1:1)
2. **Naming consistency**: File name ID matches method name ID for every case
3. **Import validity**: All `from apps.autotest_<app>...` imports resolve
4. **Inheritance chain**: Widget extends BaseWidget, TestCase extends BaseCase
5. **skip markers**: Non-automatable cases have proper `@pytest.mark.skip`
6. **Module coverage**: Every module has a corresponding widget file

Run the diagnostic check:

```bash
python -m pytest -c pytest-tests.ini tests/ --collect-only
```

## YouQu PO Pattern — Inheritance Chain Reference

The generated code must follow this exact inheritance structure:

```
Widget Layer (operations):
  src.Src
    └── widget/base_widget.py::BaseWidget(APP_NAME="app-name", DESC="/usr/bin/app-name")
         └── widget/<module>_widget.py::<Module>Widget

Assert Layer (verification):
  src.assert_common.AssertCommon
    └── <app>_assert.py::<App>Assert
         └── case/base_case.py::BaseCase(APP_NAME="app-name")
              └── case/test_<case>_<nnn>.py::Test<Case>
```

### Available Assertion Methods (from AssertCommon)

| Method | Purpose | Example |
|--------|---------|---------|
| `assert_true(expect)` | Boolean assertion | `self.assert_true(widget.exists)` |
| `assert_false(expect)` | Negation assertion | `self.assert_false(widget.is_hidden)` |
| `assert_equal(expect, actual)` | Equality check | `self.assert_equal("expected", actual)` |
| `assert_process_status(expect, app)` | Process running | `self.assert_process_status(True, "deepin-music")` |
| `assert_window_amount(app, expect)` | Window count | `self.assert_window_amount("deepin-music", 1)` |
| `assert_ocr_exist(*strings, **kwargs)` | OCR text exists | `self.assert_ocr_exist("确定")` |
| `assert_ocr_not_exist(*strings, **kwargs)` | OCR text absent | `self.assert_ocr_not_exist("错误")` |
| `assert_element_exist(expr)` | AT-SPI element exists | `self.assert_element_exist("$/deepin-music//Btn_Play")` |
| `assert_element_not_exist(expr)` | AT-SPI element absent | `self.assert_element_not_exist("$/deepin-music//Dialog_Error")` |
| `assert_image_exist(image, rate=0.9)` | Image on screen | `self.assert_image_exist("ok_button.png")` |
| `assert_file_exist(widget, file)` | File on disk | `self.assert_file_exist("/tmp/output.txt")` |

### Available Src Methods (from Src base class)

| Category | Key Methods | Description |
|----------|-------------|-------------|
| AT-SPI (dog) | `self.dog.find_element_by_attr("name")`, `self.dog.element_click("name")`, `self.dog.element_input("name", "text")` | AT-SPI element operations |
| OCR | `self.ocr(*strings, **kwargs)`, `self.ocr_in_window(*strings)` | Text recognition and positioning |
| Image | `self.find_image(*imgs)`, `self.image_click(*imgs)` | Template matching and clicking |
| Mouse/Key | `self.click(x, y)`, `self.right_click(x, y)`, `self.input_message("text")`, `self.hot_key("ctrl,c")` | Input operations |
| Window | `self.ui.btn_size("button_name")` | ButtonCenter coordinate lookup |
| Command | `self.run_cmd("command")` | Execute shell commands |

## Delegation Pattern

For multi-module generation, dispatch one sub-agent per batch in parallel.

Sub-agent prompt template (all 6 sections):

```
1. TASK: Generate Python test files for module "<module>" (<count> cases).
   Read the xlsx JSON batch at <batch_json_path>.
   Target app: <app_name>. Working directory: <project_root>.

2. EXPECTED OUTCOME:
   - <count> Python test files in apps/autotest_<app>/case/
   - 1 Widget file in apps/autotest_<app>/widget/<module>_widget.py
   - File naming: test_<case_name>_<nnn>.py where <nnn>=0-indexed batch position+1
   - Non-automatable cases: @pytest.mark.skip decorator + pass body

3. REQUIRED TOOLS: read, write, edit

4. MUST DO:
   - Read the xlsx JSON batch file to get case data
   - Read the existing base_widget.py and base_case.py for inheritance reference
   - Use ONLY youqu-mcp for AT-SPI tree acquisition (window_focus, atspi_find_element, screenshot_save)
   - For each case, extract the test intent from "steps" and "expected" fields
   - Map operations to concrete Widget methods using real AT-SPI element names
   - Follow YouQu naming: file name ID == method name ID
   - Import from apps.autotest_<app>.widget.<module>_widget
   - Use assertion methods from AssertCommon (assert_true, assert_equal, assert_process_status, etc.)
   - Non-automatable cases: use @pytest.mark.skip(reason="<reason>") — do NOT omit

5. MUST NOT DO:
   - Modify any framework source files (src/, setting/, conftest.py at project root)
   - Modify files outside apps/autotest_<app>/ directory
   - Use `@ts-ignore`, `as any`, or suppress type errors — YouQu is Python
   - Invent element names without MCP verification
   - Generate "pass" stubs for automatable cases
   - Hardcode absolute file paths

6. CONTEXT:
   - YouQu framework version: v2.14.4
   - PO inheritance: Src → BaseWidget → <Module>Widget, AssertCommon → <App>Assert → BaseCase → Test<Case>
   - Widget method naming: click_<target>_by_<strategy>(), get_<target>_<prop>(), etc.
   - AT-SPI path format: $/app_name//element_name (for youqu-mcp)
   - Skip classification rules from SKILL.md §Skip Classification table
   - Available MCP tools: youqu-mcp (atspi_find_element, window_focus, screenshot_save, keyboard_press_key, mouse_click)
```

## Pitfalls

Read @references/pitfalls.md for the complete list. Key highlights:

1. **Sub-agents must not modify framework source.** Every sub-agent prompt must
   explicitly forbid editing files outside the target `apps/autotest_<app>/` directory.

2. **AT-SPI selectors must match reality.** Never invent element names. Use
   `atspi_find_element` results as ground truth. An element named "Btn_Play" in
   code but "Btn_播放" in the tree will fail at runtime.

3. **File name ID must match method name ID.** Framework enforces this at
   collection time — `test_music_play_001.py` must contain `test_music_play_001`.
   Mismatched IDs cause the test to be silently skipped.

4. **Non-automatable cases need files too.** The 1:1 requirement means every
   source case produces a Python file. Skip cases with `@pytest.mark.skip`, don't
   omit them.

5. **Widget method granularity matters.** Each Widget method should do ONE thing.
   Don't combine multiple operations into a single method — this defeats the
   PO pattern's composability.

6. **OCR/implicit waits need padding.** After clicking elements that trigger UI
   transitions (dialog open, page switch), add `time.sleep(0.5)` or use
   `self.dog.wait_for_element()` before the next action.

7. **startapp modifies templates.** The `startapp` command performs `${VAR}`
   substitution. Any files generated after `startapp` must follow the same
   substitution pattern.

## Reference Files

- **@references/youqu-po-pattern.md** — Complete reference: inheritance chain,
  all Src methods, all assertion methods, Widget method naming conventions,
  common operation patterns (menu, dialog, file picker, input, dropdown).

- **@references/mcp-tool-reference.md** — youqu-mcp tool reference: every tool's
  purpose, parameters, return values, and usage patterns. Read before any MCP
  interaction.

- **@references/skip-classification.md** — Full skip classification rules with
  detection patterns, skip reasons, and manual review criteria.

- **@references/pitfalls.md** — Complete list of known pitfalls with root causes
  and solutions, covering generation quality, framework compatibility, and
  sub-agent issues.

- **@scripts/export_xlsx.py** — Batch export xlsx/csv rows to JSON. Use in Step 1.

- **@assets/widget_template.py** — Battle-tested Widget file template with all
  common method patterns included as comments.

- **@assets/case_template.py** — Test case file template with proper imports,
  inheritance, assertion examples, and skip marker examples.

## Quick Start

```
# 1. Export xlsx/csv to JSON batches
python3 scripts/export_xlsx.py cases.xlsx /tmp/case_batches --batch-size 10

# 2. Create YouQu APP project
youqu manage.py startapp autotest_my_app

# 3. Launch app, get AT-SPI tree via MCP
#    (use youqu-mcp tools: window_focus, atspi_find_element, screenshot_save)

# 4. LLM generates Python (this skill)
#    - Read xlsx JSON batches
#    - Classify cases (automatable / skip)
#    - Match operations against AT-SPI tree elements
#    - Generate Widget methods per module
#    - Generate test_<name>_<nnn>.py per case
#    - Non-automatable → @pytest.mark.skip

# 5. Verify
python -m pytest -c pytest-tests.ini tests/ --collect-only
```
