# MCP Tool Reference (bare names)

Tool names below are bare function names. MCP clients prefix them with the
server name (e.g. if server is configured as `youqu-mcp`, the actual tool
name becomes `window_focus`).

## Window Management

| Tool | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `window_focus` | `app_name`: application name, `config_path`?: ui.ini path | — | Bring app window to front |
| `window_get_count` | `app_name`: app, `config_path`?: path | Integer count | Number of windows |
| `window_get_center` | `app_name`: app, `config_path`?: path | `{x, y}` | Window center coordinates |
| `window_get_info` | `app_name`: app, `config_path`?: path | `str(info)` (stringified) | Position, size, geometry as string |
| `window_close` | `app_name`: app, `config_path`?: path | — | Close app window (AT-SPI action, xdotool fallback) |

## AT-SPI Element Inspection

| Tool | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `atspi_find_element` | `app_name`: app, `expr`: AT-SPI path, `index`?=0 | `str(element)` (stringified) | Find element by path expression |
| `atspi_find_and_click` | `app_name`, `expr`, `index`?=0 | — | Find and click element |
| `atspi_find_and_right_click` | `app_name`, `expr`, `index`?=0 | — | Find and right-click |
| `atspi_get_children_text` | `app_name`, `element_expr` | Text array | Get children text of element |
| `atspi_dump_tree` | `app_name` | Tree string | Full AT-SPI tree dump |

### AT-SPI Path Expression Syntax

```
$/<app_name>//<element_attr>  — search the app's tree
$/                          — search from root
$/<role>                    — match by AT-SPI role (e.g., push button, menu item)
$/<name>                    — match by accessible name
$/<name>/<role>             — combined match
$/<app>//<child>            — find child under specific app
```

## Input Simulation

| Tool | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `keyboard_press_key` | `key`: key name or combo (`+` separated) | — | Press keyboard key |
| `keyboard_hot_key` | `keys`: comma-separated (`"ctrl,c"`) | — | Press key combo |
| `keyboard_type_text` | `text`: string | — | Type text (supports Chinese) |
| `mouse_click` | `x`, `y`: coordinates | — | Left-click at position |
| `mouse_double_click` | `x`, `y` | — | Double-click at position |
| `mouse_right_click` | `x`, `y` | — | Right-click at position |
| `mouse_move_to` | `x`, `y`, `duration`?=0.4 | — | Move mouse to position |
| `mouse_scroll` | `amount`: integer | — | Scroll (positive=up) |

## Screenshot

| Tool | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `screenshot_save` | — | File path | Full-screen screenshot (no VLM required) |

## Process Management

| Tool | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `system_get_process_status` | `process_name` | Bool/status | Check process running |
| `system_kill_process` | `process_name` | — | Kill process (blacklist-protected) |
| `system_run_command` | `command` | Output | Execute read-only command |
| `app_launch` | `command`, `wait_seconds`?=3 | — | Launch app with args (e.g. `'/usr/bin/deepin-reader /path/to/doc.pdf'`), blacklist-protected |
| `get_screen_size` | — | `{width, height}` | Screen resolution |

## Assertions

| Tool | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `assert_element_exists` | `expr`: AT-SPI path | `{assertion: "PASS"/"FAIL"}` | Assert element visible |
| `assert_element_not_exists` | `expr`: AT-SPI path | `{assertion: "PASS"/"FAIL"}` | Assert element absent |
| `assert_image_exists` | `image_path`, `rate`?=0.8 | `{assertion: "PASS"/"FAIL"}` | Assert image on screen |
| `assert_file_exists` | `file_path` | `{assertion: "PASS"/"FAIL"}` | Assert file on disk |
| `assert_process_running` | `app_name` | `{assertion: "PASS"/"FAIL"}` | Assert process running |
| `assert_window_count` | `app_name`, `expected` | `{assertion: "PASS"/"FAIL"}` | Assert window count |

## VLM Tools

| Tool | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `vlm_agent_run` | `instruction`, `max_iterations`?=10 | Agent result | Autonomous VLM execution |
| `vlm_click` | `description` | `{x, y, confidence, message}` | VLM-located click |
| `vlm_assert_visual` | `assertion`, `expected` | `{verdict, confidence, reason}` | VLM visual verification |

## D-Bus

| Tool | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `dbus_get_property` | `bus_type` ("session"/"system"), `service`, `path`, `interface_name`, `property_name` | `str(value)` | Read D-Bus property |

## Inspection Workflow Example

### Step-by-step: Get app's AT-SPI tree

```
# 1. Ensure app is running and focused
window_focus(app_name="deepin-music")

# 2. Get window position/size (for coordinate calculations)
window_get_info(app_name="deepin-music")

# 3. Find root elements by role
atspi_find_element(app_name="deepin-music", expr="$/push button")
atspi_find_element(app_name="deepin-music", expr="$/menu item")

# 4. Find named elements
atspi_find_element(app_name="deepin-music", expr="Btn_播放")
atspi_find_element(app_name="deepin-music", expr="Btn_上一首")

# 5. Get children of containers
atspi_get_children_text(app_name="deepin-music", element_expr="$/deepin-music//list view")

# 6. Screenshot for visual reference
screenshot_save()
```

### Navigating menus

```
# DTK main menu: click hamburger, then item
atspi_find_and_click(app_name="deepin-music", expr="主菜单")
atspi_find_and_click(app_name="deepin-music", expr="关于")

# Or use keyboard shortcut
keyboard_hot_key(keys="ctrl,o")
```

### Navigating file dialogs

```
# Open file dialog
atspi_find_and_click(app_name="deepin-music", expr="Btn_打开文件")

# Focus path bar and type path
keyboard_hot_key(keys="ctrl,l")
keyboard_type_text(text="/home/user/test.mp3")
keyboard_press_key(key="Return")
```

## Safety Constraints

When using MCP tools, be aware of these constraints:
- `system_kill_process` has a blacklist (systemd, Xorg, dde-session, etc.)
- `system_run_command` allows read-only commands (ps, dpkg-query, gsettings, ls, cat, find, env, echo, ss, etc.)
- `app_launch` has the same blacklist as `system_kill_process` (cannot launch protected processes)
- `keyboard_press_key` blocks dangerous combos (alt+F4, ctrl+alt+del, etc.)
- `screenshot_save` outputs to a fixed evidence directory (no VLM required)
- `keyboard_press_key` uses `+` separator (e.g. `"ctrl+a"`), `keyboard_hot_key` uses `,` (e.g. `"ctrl,c"`)
- `vlm_agent_run` clamps `max_iterations` to 1-20

## Return Value Conventions

All tools return `{"success": true/false, ...}`. Two error layers:
- **System error**: `{"success": false, "error": "..."}` — tool failed to execute
- **Assertion failure**: `{"success": true, "assertion": "FAIL", "reason": "..."}` — tool ran, assertion did not hold
