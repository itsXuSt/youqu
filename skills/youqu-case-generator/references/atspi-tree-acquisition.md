# AT-SPI Tree Acquisition Guide

How to capture real element names, roles, and structure from running desktop
applications for generating accurate YouQu test code.

## Prerequisites

### Environment Variables

```bash
echo "DISPLAY=$DISPLAY"              # :0
echo "XDG_SESSION_TYPE=$XDG_SESSION_TYPE"  # x11 or wayland
echo "AT_SPI_BUS_ADDRESS=$AT_SPI_BUS_ADDRESS"
echo "QT_ACCESSIBILITY=$QT_ACCESSIBILITY"
```

If `AT_SPI_BUS_ADDRESS` is empty:

```bash
AT_SPI_BUS_ADDRESS=$(ss -lxp 2>/dev/null | grep at-spi | grep -oP 'unix:path=\K[^ ]*' | head -1)
# Typical: unix:path=/run/user/<uid>/at-spi/bus_0
```

### Required for Qt/DTK Apps

| Variable | Value | Notes |
|----------|-------|-------|
| `DISPLAY` | `:0` | X11 session |
| `AT_SPI_BUS_ADDRESS` | `unix:path=/run/user/<uid>/at-spi/bus_0` | AT-SPI bus |
| `QT_ACCESSIBILITY` | `1` | Enable Qt a11y |
| `QT_LINUX_ACCESSIBILITY_ALWAYS_ON` | `1` | Force Qt a11y on |

## Launch the App

```bash
pkill -9 <app_name> 2>/dev/null; sleep 1

DISPLAY=:0 \
AT_SPI_BUS_ADDRESS=unix:path=/run/user/$(id -u)/at-spi/bus_0 \
QT_ACCESSIBILITY=1 \
QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1 \
nohup <app_executable> >/dev/null 2>&1 &
sleep 3
```

## Verify App is Accessible

Use youqu-mcp tools:

```
youqu-mcp_window_focus(app_name="<app_name>")
youqu-mcp_window_get_info(app_name="<app_name>")
```

If `window_focus` succeeds and `get_info` returns window geometry, the app is ready.

## Primary Method: youqu-mcp

```
# Find elements by AT-SPI path expression
youqu-mcp_atspi_find_element(app_name="<app_name>", expr="$/push button")
youqu-mcp_atspi_find_element(app_name="<app_name>", expr="<element_name>")
youqu-mcp_atspi_find_and_click(app_name="<app_name>", expr="<element_name>")

# Get children text (for list/tree views)
youqu-mcp_atspi_get_children_text(app_name="<app_name>", element_expr="$/<app_name>//list view")

# Screenshot for visual reference
youqu-mcp_screenshot_save()
```

**AT-SPI path expression syntax:**
- `$/app_name//element` — search under app
- `$/role` — search by role (e.g., `$/push button`, `$/menu item`)
- `$/name` — search by accessible name directly
- `$/name/role` — combined search

## Fallback Method: pyatspi Script

When `atspi_find_element` fails to locate elements (common with DTK apps that
use internal class names), dump the complete tree:

```python
import os, gi
os.environ['AT_SPI_BUS_ADDRESS'] = 'unix:path=/run/user/<uid>/at-spi/bus_0'
gi.require_version('Atspi', '2.0')
from gi.repository import Atspi

def dump_tree(obj, depth=0, max_depth=6):
    if depth > max_depth:
        return
    name = obj.get_name()
    role = obj.get_role_name()
    print('  ' * depth + f'{role}: "{name}"')
    for i in range(obj.get_child_count()):
        child = obj.get_child_at_index(i)
        if child:
            dump_tree(child, depth + 1, max_depth)

desktop = Atspi.get_desktop(0)
for i in range(desktop.get_child_count()):
    app = desktop.get_child_at_index(i)
    if app.get_name() == '<app_name>':
        for j in range(app.get_child_count()):
            window = app.get_child_at_index(j)
            dump_tree(window, max_depth=8)
```

**When to use this fallback:**
- `atspi_find_element` returns "未找到" for known visible elements
- DTK apps use internal class names (e.g., `DTitlebarDWindowOptionButton`
  instead of `主菜单`)
- Need to inspect transient dialogs/popup menus

## Capture Different UI States

AT-SPI trees change with UI state. Capture each separately:

| State | How to Trigger | What to Capture |
|-------|---------------|-----------------|
| Main window | App launch | Titlebar, tab bar, content area |
| Main menu | Click menu button | All menu items, submenus |
| Settings | Menu → Settings | Left nav, right content widgets |
| Search | Ctrl+Alt+F or app shortcut | Search input, buttons |
| About | Menu → About | Dialog title, close button |
| Right-click menu | Right-click on content | All context menu items |

**Workflow:**
1. Trigger the UI state (click menu, press shortcut)
2. Wait for UI to settle (`sleep 0.5-1.0`)
3. Dump tree (pyatspi fallback for complete output)
4. Screenshot for visual cross-reference
5. Restore main window state (Escape)

## Known Limitations

1. **Right-click context menus may not register AT-SPI.** Use coordinate-based
   clicking (`self.right_click(x, y)`) + OCR/VLM or keyboard shortcuts.

2. **Empty-named elements.** Many buttons/fillers have `""` as accessible name.
   Use index, role-based filtering, or coordinates instead.

3. **Combo box names are dynamic.** A font dropdown showing "Noto Sans Mono"
   has that value as its name, not "字体". Name changes with selection.

4. **Transient dialogs.** Popup menus/dialogs only exist while visible.
   Dump immediately after triggering.

## Key Things to Extract

From the captured tree, record:
- **Element names** — for `dog.element_click("real_name")` or `dog.find_element_by_attr("real_name")`
- **Element roles** — button, menu item, combo box, etc.
- **Menu item labels** — for menu navigation
- **Dialog structure** — for multi-step dialog workflows
- **Widget hierarchy** — for nested navigation (settings > advanced > cursor)
- **Non-AT-SPI elements** — mark for OCR/coordinate fallback

## Persist Results

Save to `apps/autotest_<app>/docs/at-spi-tree.md` with:
- Environment info (date, XDG_SESSION_TYPE, app version)
- Full element tables per UI state
- Known limitations encountered
