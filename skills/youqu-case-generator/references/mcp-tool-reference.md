# youqu-mcp Tool Reference

All tools available through the `youqu-mcp` MCP server for YouQu framework
test case generation. These tools provide AT-SPI introspection, window
management, input simulation, and assertions at the MCP level.

## Window Management

| Tool | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `youqu-mcp_window_focus` | `app_name`: application name, `config_path`?: ui.ini path | — | Bring app window to front |
| `youqu-mcp_window_get_count` | `app_name`: app, `config_path`?: path | Integer count | Number of windows |
| `youqu-mcp_window_get_center` | `app_name`: app, `config_path`?: path | `{x, y}` | Window center coordinates |
| `youqu-mcp_window_get_info` | `app_name`: app, `config_path`?: path | Window info dict | Position, size, geometry |

## AT-SPI Element Inspection

| Tool | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `youqu-mcp_atspi_find_element` | `app_name`: app, `expr`: AT-SPI path, `index`?=0 | Element info dict | Find element by path expression |
| `youqu-mcp_atspi_find_and_click` | `app_name`, `expr`, `index`?=0 | — | Find and click element |
| `youqu-mcp_atspi_find_and_right_click` | `app_name`, `expr`, `index`?=0 | — | Find and right-click |
| `youqu-mcp_atspi_get_children_text` | `app_name`, `element_expr` | Text array | Get children text of element |

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
| `youqu-mcp_keyboard_press_key` | `key`: key name/comb | — | Press keyboard key |
| `youqu-mcp_keyboard_hot_key` | `keys`: "ctrl,c" | — | Press key combo |
| `youqu-mcp_keyboard_type_text` | `text`: string | — | Type text (supports Chinese) |
| `youqu-mcp_mouse_click` | `x`, `y`: coordinates | — | Left-click at position |
| `youqu-mcp_mouse_double_click` | `x`, `y` | — | Double-click at position |
| `youqu-mcp_mouse_right_click` | `x`, `y` | — | Right-click at position |
| `youqu-mcp_mouse_move_to` | `x`, `y`, `duration`?=0.4 | — | Move mouse to position |
| `youqu-mcp_mouse_scroll` | `amount`: integer | — | Scroll (positive=up) |

## Screenshot

| Tool | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `youqu-mcp_screenshot_save` | — | File path | Full-screen screenshot |

## Process Management

| Tool | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `youqu-mcp_system_get_process_status` | `process_name` | Bool/status | Check process running |
| `youqu-mcp_system_kill_process` | `process_name` | — | Kill process (blacklist-protected) |
| `youqu-mcp_system_run_command` | `command` | Output | Execute read-only command |
| `youqu-mcp_get_screen_size` | — | `{width, height}` | Screen resolution |

## Assertions

| Tool | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `youqu-mcp_assert_element_exists` | `expr`: AT-SPI path | Pass/Fail | Assert element visible |
| `youqu-mcp_assert_element_not_exists` | `expr`: AT-SPI path | Pass/Fail | Assert element absent |
| `youqu-mcp_assert_image_exists` | `image_path`, `rate`?=0.8 | Pass/Fail | Assert image on screen |
| `youqu-mcp_assert_file_exists` | `file_path` | Pass/Fail | Assert file on disk |
| `youqu-mcp_assert_process_running` | `app_name` | Pass/Fail | Assert process running |
| `youqu-mcp_assert_window_count` | `app_name`, `expected` | Pass/Fail | Assert window count |

## VLM Tools

| Tool | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `youqu-mcp_vlm_agent_run` | `instruction`, `max_iterations`?=10 | Agent result | Autonomous VLM execution |
| `youqu-mcp_vlm_click` | `description` | — | VLM-located click |
| `youqu-mcp_vlm_assert_visual` | `assertion`, `expected` | Pass/Fail | VLM visual verification |

## D-Bus

| Tool | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `youqu-mcp_dbus_get_property` | `bus_type`, `service`, `path`, `interface_name`, `property_name` | Value | Read D-Bus property |

## Inspection Workflow Example

### Step-by-step: Get app's AT-SPI tree

```
# 1. Ensure app is running and focused
youqu-mcp_window_focus(app_name="deepin-music")

# 2. Get window position/size (for coordinate calculations)
youqu-mcp_window_get_info(app_name="deepin-music")

# 3. Find root elements by role
youqu-mcp_atspi_find_element(app_name="deepin-music", expr="$/push button")
youqu-mcp_atspi_find_element(app_name="deepin-music", expr="$/menu item")

# 4. Find named elements
youqu-mcp_atspi_find_element(app_name="deepin-music", expr="Btn_播放")
youqu-mcp_atspi_find_element(app_name="deepin-music", expr="Btn_上一首")

# 5. Get children of containers
youqu-mcp_atspi_get_children_text(app_name="deepin-music", element_expr="$/deepin-music//list view")

# 6. Screenshot for visual reference
youqu-mcp_screenshot_save()
```

### Navigating menus

```
# DTK main menu: click hamburger, then item
youqu-mcp_atspi_find_and_click(app_name="deepin-music", expr="主菜单")
youqu-mcp_atspi_find_and_click(app_name="deepin-music", expr="关于")

# Or use keyboard shortcut
youqu-mcp_keyboard_hot_key(keys="ctrl,o")
```

### Navigating file dialogs

```
# Open file dialog
youqu-mcp_atspi_find_and_click(app_name="deepin-music", expr="Btn_打开文件")

# Focus path bar and type path
youqu-mcp_keyboard_hot_key(keys="ctrl,l")
youqu-mcp_keyboard_type_text(text="/home/user/test.mp3")
youqu-mcp_keyboard_press_key(key="Return")
```

## Safety Constraints

When using MCP tools, be aware of these constraints:
- `system_kill_process` has a blacklist (systemd, Xorg, dde-session, etc.)
- `system_run_command` only allows read-only commands (ps, dpkg-query, gsettings, etc.)
- `keyboard_press_key` blocks dangerous combos (alt+F4, ctrl+alt+del, etc.)
- `screenshot_save` outputs to a fixed evidence directory
