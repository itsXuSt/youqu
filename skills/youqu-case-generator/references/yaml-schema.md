# YAML Test Case Schema Reference

Complete reference for YouQu YAML test case format — all actions, assertions,
element registry (elements.yaml), and ref-based element resolution.

## Elements Registry (MANDATORY)

`autotest/yaml/elements.yaml` is the single source of truth for all UI elements
referenced by test cases. Every `ref` in test YAML must resolve to an entry here.

### Format

```yaml
# Element aliases for <app-name>
app: <app-name>

elements:
  # ===== AT-SPI elements (name/role) =====
  # Used by: element_action, element_set_value, asserts
  ok_button:
    name: "确定"
  file_dialog:
    name: "选择文件"
    role: "dialog"
  settings_tab:
    name: "设置"
    role: "page tab"

  # ===== Coordinate elements (x/y) =====
  # Used by: mouse_click, mouse_right_click, mouse_double_click, mouse_drag
  app_center:
    x: 500
    y: 300
  toolbar_button:
    x: 250
    y: 45

  # ===== Menu navigation (menu) =====
  # Used by: main_menu_comb
  # Keyboard arrow-key navigation (↑↓ for items, ←→ for submenus, Enter to confirm)
  open_file:
    menu: ["文件", "打开"]
  preferences:
    menu: ["编辑", "首选项"]

  # ===== Context menu (x/y + menu) =====
  # Used by: context_menu_comb
  # Right-click at (x,y), then keyboard-navigate to menu item
  context_copy:
    x: 450
    y: 200
    menu: ["复制"]
  context_delete:
    x: 450
    y: 250
    menu: ["更多", "删除"]

  # ===== Element + menu (click element first, then menu) =====
  # Used by: main_menu_comb
  # Click the element, then keyboard-navigate to menu item
  help_menu:
    name: "帮助"
    role: "menu"
    menu: ["关于"]

# Legacy inline definitions (deprecated, prefer elements.yaml)
# Inline selector/x/y/items in test YAML is NOT supported —
# all element definitions must be in elements.yaml
```

### Element Type Reference

| Fields | Used By | Description |
|--------|---------|-------------|
| `name`, `role` | element_action, element_set_value, assert selectors | AT-SPI element lookup |
| `x`, `y` | mouse_click, mouse_right_click, mouse_double_click, mouse_drag | Coordinate-based actions |
| `menu` | main_menu_comb | Keyboard menu navigation |
| `x`, `y`, `menu` | context_menu_comb | Right-click + keyboard menu |
| `name`, `role`, `menu` | main_menu_comb | Click element + keyboard menu |

## Top-Level Structure

```yaml
name: "测试用例标题"
app: "app-name"
screenshot: false       # enable automatic screenshots after each step
vars:
  KEY: "value"

setup:
  - action: session_start
    command: "app-name"
    wait: 3.0

steps:
  - name: "步骤描述"
    action: <action_type>
    ref: <element_alias>    # references elements.yaml entry
    # step-specific params (see Action Reference below)
    wait_after: 500      # ms delay after step (optional)
    wait_for:            # poll-until condition (optional, uses inline selectors)
      selector: {...}
      timeout: 5000
      interval: 200
    assert:              # assertions after step (optional, uses inline selectors)
      - type: <assert_type>
        # assert-specific params

teardown:
  - action: session_stop
```

**Ref resolution**: All actions use `ref` to reference elements.yaml entries.
Inline `selector`, `x`, `y`, `items` are **not allowed** in test YAML — this
prevents element definitions from being scattered across multiple test files.
The executor resolves `ref` to the corresponding elements.yaml entry at runtime.

**Exception**: `wait_for` and `assert` blocks use inline selectors. These target
transient UI state (dialogs, notifications, dynamic content) that is situational,
not globally registered elements.

## Action Reference

### Session Lifecycle

| Action | Parameters | Description |
|--------|-----------|-------------|
| `session_start` | `command` (str), `wait` (float, seconds) | Launch app process, wait for window |
| `session_stop` | — | Kill all app processes via `pkill` |

### Keyboard

| Action | Parameters | Description |
|--------|-----------|-------------|
| `keyboard_press` | `keys` (str) | Single key or combo: `"Return"`, `"ctrl+a"` |
| `keyboard_hot_key` | `keys` (str) | Key combination: `"ctrl,c"` |
| `keyboard_type` | `text` (str) | Type text string via xdotool/ydotool |

### Mouse

| Action | Parameters | Description |
|--------|-----------|-------------|
| `mouse_click` | `ref` (str) | Left click — resolve x/y from elements.yaml |
| `mouse_right_click` | `ref` (str) | Right click — resolve x/y from elements.yaml |
| `mouse_double_click` | `ref` (str) | Double click — resolve x/y from elements.yaml |
| `mouse_scroll` | `amount` (int) | Scroll (±amount, positive=up) |
| `mouse_drag` | `ref` (str) | Drag to coordinates — resolve x/y from elements.yaml |

### AT-SPI Element Actions

| Action | Parameters | Description |
|--------|-----------|-------------|
| `element_action` | `ref` (str), `do` (str) | AT-SPI operation: `"click"`, `"right_click"`, `"double_click"` |
| `element_set_value` | `ref` (str), `text` (str) | Set text value on input element |

Both resolve `ref` from elements.yaml to get the element's `name`/`role` attributes.

### Menu Navigation (Keyboard-based)

| Action | Parameters | Description |
|--------|-----------|-------------|
| `main_menu_comb` | `ref` (str) | Keyboard-navigate menu. Resolve from elements.yaml (`menu` field or `name`+`menu`). |
| `context_menu_comb` | `ref` (str) | Right-click + keyboard-navigate context menu. Resolve from elements.yaml (`x`/`y`+`menu` fields). |

Menu navigation uses arrow keys (↑↓←→) and Enter — no mouse hover needed.
See `src/menu_nav.py`.

### D-Bus

| Action | Parameters | Description |
|--------|-----------|-------------|
| `dbus_call` | `value` (dict) | Call D-Bus method. `value`: `{bus_type, dbus_name, object_path, interface, method, args}` |
| `dbus_get_property` | `value` (dict) | Read D-Bus property. `value`: `{bus_type, dbus_name, object_path, interface, property}` |

### Utility

| Action | Parameters | Description |
|--------|-----------|-------------|
| `wait` | `wait` (float, seconds) | Sleep for N seconds |
| `screenshot` | — | Capture screen to evidence directory |

## Assert Reference

### Element Presence / State

| Assert Type | Parameters | Description |
|-------------|-----------|-------------|
| `element_visible` | `selector` (dict) | Element exists in AT-SPI tree |
| `element_not_visible` | `selector` (dict) | Element does NOT exist |
| `element_numbers` | `selector` (dict), `number` (int) | Exact count of matching elements |
| `element_text` | `selector` (dict), `expected` (str) | Element text equals expected |

### Process

| Assert Type | Parameters | Description |
|-------------|-----------|-------------|
| `process_running` | `app` (str) | Process is running |
| `process_not_running` | `app` (str) | Process is NOT running |

### File

| Assert Type | Parameters | Description |
|-------------|-----------|-------------|
| `file_exists` | `path` (str) | File exists on disk |
| `file_not_exists` | `path` (str) | File does NOT exist |

### Image & OCR

| Assert Type | Parameters | Description |
|-------------|-----------|-------------|
| `image_exist` | `path` (str) | Template image matches screen region |
| `image_not_exist` | `path` (str) | Template image NOT on screen |
| `ocr_exist` | `text` (str) | OCR text exists on screen |
| `ocr_not_exist` | `text` (str) | OCR text NOT on screen |

### Window

| Assert Type | Parameters | Description |
|-------------|-----------|-------------|
| `window_size` | `expected` (str), `actual` (str) | Window dimensions match |

### D-Bus

| Assert Type | Parameters | Description |
|-------------|-----------|-------------|
| `dbus_property` | `value` (dict) | D-Bus property equals expected (`value.expected` field) |

## Selector Format (assert / wait_for only)

Assert and wait_for blocks use inline selectors (not ref). These target
transient or expected UI state — not globally registered elements.

### Simple Selectors

```yaml
# By accessible name
selector:
  name: "确定"

# By AT-SPI role
selector:
  role: "dialog"

# Combined
selector:
  name: "确定"
  role: "push button"

# By index
selector:
  index: 0
```

### Supported Selector Fields

| Field | Type | Match Behavior |
|-------|------|---------------|
| `name` | str | Accessible name attribute |
| `role` | str | AT-SPI role (e.g. `"push button"`, `"menu item"`) |
| `description` | str | Description attribute |
| `index` | int | Select nth match (0-based) |

## Variable Substitution

Use `${VAR_NAME}` in any string field. Variables are defined in the top-level
`vars:` section and substituted at parse time (before execution).

```yaml
vars:
  PDF_PATH: "/home/user/test.pdf"
  APP_BIN: "/usr/bin/deepin-reader"
setup:
  - action: session_start
    command: "${APP_BIN} ${PDF_PATH}"
steps:
  - action: element_set_value
    selector: {name: "路径输入框"}
    text: "${PDF_PATH}"
```

## Wait Conditions

Steps can declare `wait_for` to poll the AT-SPI tree until a condition is met
before executing the step action.

```yaml
- name: "点击按钮，等待对话框出现"
  action: element_action
  selector: {name: "打开"}
  do: "click"
  wait_for:
    selector: {role: "dialog"}
    timeout: 5000     # ms, default 5000
    interval: 200     # ms poll interval, default 200
```

If `wait_for` times out, the step raises `TimeoutError`. The poll uses
`find_element_by_attr` (not deep tree scan) for performance.

## Non-Automatable Cases

Non-automatable cases are documented with a comment header. The YAML body
is a minimal stub:

```yaml
# NON-AUTOMATABLE: 触摸操作无法自动化
name: "手势缩放测试"
app: "app"
setup: []
steps: []
teardown: []
```

This preserves the case in version control without generating false test results.

## File Naming

YAML files follow the same convention as Python: `test_<name>_<nnn>.yaml`
where `<nnn>` is a 3-digit padded ID. The `name` field in the YAML should
match the test description.

Files reside in `autotest/yaml/`. They're auto-discovered when
`yaml_files = yaml` is set in `autotest/pytest.ini`.
