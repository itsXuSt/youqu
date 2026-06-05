# YAML Test Case Schema Reference

Complete reference for YouQu YAML test case format — all actions, assertions, and
selector patterns supported by the YAML executor (`src/yaml_test/executor.py`).

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
    # step-specific params (see Action Reference below)
    wait_after: 500      # ms delay after step (optional)
    wait_for:            # poll-until condition (optional)
      selector: {...}
      timeout: 5000
      interval: 200
    assert:              # assertions after step (optional)
      - type: <assert_type>
        # assert-specific params

teardown:
  - action: session_stop
```

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
| `mouse_click` | `x` (int), `y` (int) | Left click at coordinates |
| `mouse_right_click` | `x` (int), `y` (int) | Right click at coordinates |
| `mouse_double_click` | `x` (int), `y` (int) | Double click at coordinates |
| `mouse_scroll` | `amount` (int) | Scroll (±amount, positive=up) |
| `mouse_drag` | `x` (int), `y` (int) | Drag to coordinates |

### AT-SPI Element Actions

| Action | Parameters | Description |
|--------|-----------|-------------|
| `element_action` | `selector` (dict), `do` (str) | AT-SPI operation: `"click"`, `"right_click"`, `"double_click"` |
| `element_set_value` | `selector` (dict), `text` (str) | Set text value on input element |

### Menu Navigation (Keyboard-based)

| Action | Parameters | Description |
|--------|-----------|-------------|
| `main_menu_comb` | `items` (list of str) | Keyboard-navigate main menu, e.g. `["文件", "打开"]` |
| `context_menu_comb` | `x` (int), `y` (int), `items` (list of str) | Right-click at (x,y) + keyboard-navigate context menu |

Menu navigation uses arrow keys (↑↓←→) and Enter — no mouse hover needed.
The framework opens the menu, navigates to each item level, opens/expands submenus,
and confirms on the final item. See `src/menu_nav.py`.

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

## Selector Format

Selectors are JSON-like dictionaries (YAML mapping), NOT AT-SPI path expressions.
The executor converts selectors to AT-SPI `find_element_by_attr` calls internally.

### Simple Selectors

```yaml
# By accessible name
selector:
  name: "确定"

# By AT-SPI role
selector:
  role: "push button"

# Combined (name + role)
selector:
  name: "确定"
  role: "push button"

# By index (nth match in list)
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

Unknown fields are added as generic AT-SPI attribute filters.

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
