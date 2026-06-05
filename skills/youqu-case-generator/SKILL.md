---
name: youqu-case-generator
version: "0.2.0"
description: >
  Generate YouQu Python test projects from xlsx/csv or feature descriptions.
  Use whenever: xlsx转py用例, csv转py用例, 生成YouQu用例, generate YouQu tests,
  批量生成测试用例, youqu make, 创建autotest, AT-SPI用例生成.
---

# YouQu Case Generator

Generate complete, executable YouQu Python test projects from xlsx/csv test case
documents. Core principle: LLM understands test intent + youqu-mcp provides the real
AT-SPI element tree → produces genuine operations, not trivial stubs.

## Two Operating Modes

- **xlsx/csv-driven**: Full regression suite from structured spreadsheet (id, title,
  module, precondition, steps, expected, priority).
- **feature-driven**: New feature cases from PR description, issue, requirement doc,
  or code diff. Extract testable scenarios manually, then generate.

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
└── report/                  # test reports output
```

**Naming**: `youqu make terminal` creates `autotest/` with:
- `BaseCase.APP_NAME = "terminal"`
- `BaseWidget.APP_NAME = "terminal"`
- `BaseWidget.DESC = "/usr/bin/terminal"`
- Widget class: `TerminalWidget`
- Sample test: `TestTerminal.test_terminal_001`

**Customize `DESC`** in `base_widget.py` if the binary path differs
(e.g. `/usr/bin/deepin-terminal`).

### Step 3: Acquire Live AT-SPI Tree

Launch the target app and capture its accessibility tree. This reveals real element
names and structure — without it, generated code would guess at selectors.

**Full procedure**: See `@references/atspi-tree-acquisition.md`.

**Key points:**
- Set environment: `DISPLAY`, `AT_SPI_BUS_ADDRESS`, `QT_ACCESSIBILITY`
- Verify via `youqu-mcp_window_focus` and `youqu-mcp_window_get_info`
- Primary: `youqu-mcp_atspi_find_element` / `youqu-mcp_screenshot_save`
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

---

## Delegation Pattern

For multi-module generation, dispatch one sub-agent per batch in parallel.

**Sub-agent prompt template:**

```
1. TASK: Generate Python test files for module "<module>" (<count> cases).
   Read JSON batch at <batch_json_path>.
   Target app: <app_name>. Working dir: <project_root>.

2. EXPECTED OUTCOME:
   - <count> Python files in autotest/case/
   - 1 Widget file in autotest/widget/<module>_widget.py
   - File naming: test_<name>_<nnn>.py (<nnn>=3-digit padded batch position)
   - Non-automatable: @pytest.mark.skip + pass body

3. REQUIRED TOOLS: read, write, edit

4. MUST DO:
   - Read the JSON batch file for case data
   - Read existing base_widget.py and base_case.py for inheritance reference
   - Read autotest/docs/at-spi-tree.md for real element names
   - Use youqu-mcp for AT-SPI tree acquisition (window_focus, atspi_find_element, screenshot_save)
   - If atspi_find_element fails, use pyatspi fallback (see @references/atspi-tree-acquisition.md)
   - Map operations to concrete Widget methods using real AT-SPI element names
   - Follow naming: file ID == method ID
   - Non-automatable → @pytest.mark.skip(reason="..."), never omit

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

---

## Reference Files

| File | Purpose |
|------|---------|
| `@references/youqu-po-pattern.md` | Inheritance chain, Src methods, assertions, Widget conventions |
| `@references/mcp-tool-reference.md` | youqu-mcp tool reference with parameters and usage |
| `@references/skip-classification.md` | Full skip rules with detection patterns |
| `@references/atspi-tree-acquisition.md` | AT-SPI tree capture procedure (env, launch, dump, persist) |
| `@references/pitfalls.md` | Complete pitfalls list with root causes |
| `@scripts/export_xlsx.py` | Batch export xlsx/csv rows to JSON |
| `@assets/widget_template.py` | Widget file template with common method patterns |
| `@assets/case_template.py` | Test case file template |
