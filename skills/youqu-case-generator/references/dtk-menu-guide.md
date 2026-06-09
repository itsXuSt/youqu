# DTK Menu Operations Guide

## Main Menu (主菜单)

### How it works

DTK applications expose the main menu through the titlebar. The menu system
has two implementation strategies:

1. **Standard QMenuBar** — persistent menu bar with items in the AT-SPI tree.
   Example: deepin-terminal's "主题" menu under the hamburger button.

2. **DTK DMenu::exec()** — transient popup menus that are NOT in the AT-SPI
   accessibility tree. Items only appear via AT-SPI events (focus-changed).
   Example: right-click context menus in file managers.

### YAML usage

Register in `elements.yaml`:

```yaml
# Menu path only (keyboard navigation from menu bar)
theme_dark:
  menu: ["主题", "深色"]

# Element + menu (click element first, then navigate)
help_about:
  name: "帮助"
  role: "menu"
  menu: ["关于"]
```

Test step:

```yaml
- action: main_menu_comb
  ref: theme_dark
  wait: 0.3
```

### What happens internally

1. `MenuNavigator.open_main_menu()` — press Alt, then try clicking
   `DTitlebarDWindowOptionButton` via AT-SPI
2. Arrow keys (↓) to navigate to target item
3. Arrow keys (→) to enter submenus
4. Enter to confirm
5. Built-in sleeps: 0.1s after Alt, 0.15s after button click, 0.1s per
   arrow key press, 0.3s between submenu levels

## Context Menu (右键菜单)

### How it works

Right-click at coordinates to open a context menu, then use keyboard
navigation to select items. DTK context menus use `DMenu::exec()` which
creates transient popups.

### YAML usage

Register in `elements.yaml`:

```yaml
context_find:
  x: 989
  y: 591
  menu: ["查找"]
```

Test step:

```yaml
- action: context_menu_comb
  ref: context_find
  wait: 0.3
```

### What happens internally

1. Right-click at (x, y)
2. 0.1s wait for menu to appear
3. Navigate by focused state or AT-SPI events (see strategy below)
4. Enter to confirm
5. 0.3s wait after selection

## Navigation Strategy Chain

`MenuNavigator.navigate_to()` uses a three-strategy chain:

| Priority | Strategy | How | When it works |
|----------|----------|-----|---------------|
| 1 | Focus tracking | Scan AT-SPI tree for focused/selected menu item | Persistent menus (QMenuBar) |
| 2 | Enumeration | List all menu items in tree, navigate by index | Items visible in tree but not focused |
| 3 | Event listening | GLib main loop + AT-SPI state-changed events | Transient DMenu::exec() popups |

Strategy 3 (event listening) is the fallback for DTK right-click menus.
Once triggered, event mode persists for remaining path items.

## Common Pitfalls

1. **Menu items use internal names** — DTK menus may show display text
   different from the AT-SPI name. Use `atspi_find_element` or `atspi_get_children_text`
   to verify actual names before writing elements.yaml.

2. **First item may not be focused** — After opening a transient popup,
   no item has focused state initially. The navigator automatically falls
   through to event-based navigation.

3. **Submenu timing** — After pressing Right to enter a submenu, 0.3s
   wait is needed before the submenu items are ready. This is built into
   `navigate_to()`.

4. **Coordinates are screen-specific** — Right-click coordinates depend
   on display resolution and window position. Always document the expected
   display setup or use relative positioning.
