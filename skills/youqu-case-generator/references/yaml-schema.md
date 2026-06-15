# YAML Test Case Schema Reference

Complete reference for YouQu YAML test case format — all actions, assertions,
element registry (elements.yaml), and ref-based element resolution.

## Directory Organization

YAML test cases can be organized into subdirectories for logical grouping.
A single `elements.yaml` at the `yaml/` root is shared by all files via
upward lookup (up to 4 directory levels):

```
yaml/
├── elements.yaml          # shared element registry (found via upward lookup)
├── keyboard/
│   ├── test_kb_menu_019.yaml
│   └── test_kb_shortcut_028.yaml
├── remote/
│   ├── test_remote_add_057.yaml
│   └── test_remote_edit_058.yaml
```

Subdirectory organization gives automatic Allure report grouping — pytest-allure
uses directory paths for `parentSuite` labels. No explicit Allure tag injection
needed.

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
skip: "skip-触摸操作无法自动化"  # optional: skip this case with reason string
vars:
  KEY: "value"

setup:
  - action: session_start
    command: "app-name"
    wait: 1.0

steps:
  - name: "步骤描述"
    action: <action_type>
    ref: <element_alias>    # references elements.yaml entry
    # step-specific params (see Action Reference below)
    wait_after: 300      # ms delay after step (optional)
    wait_for:            # poll-until condition (optional, uses inline selectors)
      selector: {...}
      timeout: 3000
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
    timeout: 3000     # ms, default 3000
    interval: 200     # ms poll interval, default 200
```

If `wait_for` times out, the step raises `TimeoutError`. The poll uses
`find_element_by_attr` (not deep tree scan) for performance.

## Timing Guide (MANDATORY)

All generated YAML test cases MUST follow these timing values. Do NOT invent
your own wait durations — they are calibrated against real DTK application
behavior and MenuNavigator internals.

### Default Wait Values

| Context | Parameter | Value | Unit | Rationale |
|---------|-----------|-------|------|-----------|
| App launch | `session_start.wait` | 1.0 | seconds | DTK app cold start to window ready |
| Post-action | `step.wait` (action: mouse_click, element_action, etc.) | 0.3 | seconds | UI state transition settle time |
| Post-action | `step.wait` (menu actions: main_menu_comb, context_menu_comb) | 0.3 | seconds | MenuNavigator has built-in 0.1-0.3s sleeps; 0.3s covers the gap |
| Post-action (ms) | `step.wait_after` | 300 | milliseconds | Same as above, in ms form |
| Poll timeout | `wait_for.timeout` | 3000 | milliseconds | If element not found in 3s, it's a failure |
| Poll interval | `wait_for.interval` | 200 | milliseconds | Default poll cadence |
| Pre-teardown | Final `action: wait` step | 0.3 | seconds | Ensure last operation's effect is visible before kill |

### Rules

1. **Always add `wait: 0.3` after every operation step** — not just UI-triggering ones.
   This covers animation settle, AT-SPI tree update, and state propagation.

2. **Last step before teardown MUST have a `wait` and/or `assert`** — never
   transition directly from an operation to `session_stop`. The app needs time
   to process the last action, and the test needs to capture the result.

3. **Use `wait_for` for expected UI state changes** (dialog open, page load,
   new element appear). Prefer `wait_for` over blind `time.sleep` when you know
   what to expect.

4. **Never exceed these defaults unless verified** — if a specific operation
   genuinely needs more time (e.g., loading a large file), document why:

   ```yaml
   # NOTE: deepin-reader needs extra time to render large PDFs
   - action: element_action
     ref: open_file
     wait: 1.0
   ```

5. **`wait_for` and `step.wait` serve different purposes**:
   - `wait_for`: Poll for a **known target** element/state → proceed when found
   - `step.wait`: Blind sleep after action → covers unknown UI transitions
   - Use both when needed: `wait_for` for the target, `wait` as safety margin

## Non-Automatable Cases (skip field)

Non-automatable cases use the top-level `skip` field with a reason string.
The case body retains its original setup/steps/teardown for reference,
but the framework pre-filters it before execution — it is never sent to pytest.

```yaml
name: "手势缩放测试"
app: "app"
skip: "skip-触摸操作无法自动化"
setup:
  - action: session_start
    command: "app"
steps:
  - name: "双指缩放图片"
    action: mouse_drag
    ref: image_center
teardown:
  - action: session_stop
```

The `skip` value follows the standardized reason format from `skip-classification.md`
(e.g. `skip-触摸操作无法自动化`, `skip-依赖特定硬件环境`).

**Benefits over empty-stub approach:**
- Original test steps preserved in YAML for human review
- Framework pre-filters before pytest — zero execution time wasted
- multica report lists skipped cases with reasons in a dedicated section
- Pass rate calculated on runnable cases only

## File Naming

YAML files follow the same convention as Python: `test_<name>_<nnn>.yaml`
where `<nnn>` is a 3-digit padded ID. The `name` field in the YAML should
match the test description.

Files reside in `autotest/yaml/` or subdirectories (e.g. `autotest/yaml/<module>/`).
They're auto-discovered when `yaml_files = yaml` is set in `autotest/pytest.ini`.
The shared `elements.yaml` at `yaml/` root is found via upward lookup.
