# YouQu PO Pattern — Complete Reference

## Inheritance Chain

```
Widget Layer (operations):
  src.Src
    └── widget/base_widget.py::BaseWidget(APP_NAME="xxx", DESC="/usr/bin/xxx")
         └── widget/<module>_widget.py::<Module>Widget

Assert Layer (verification):
  src.assert_common.AssertCommon
    └── <app>_assert.py::<App>Assert
         └── case/base_case.py::BaseCase(APP_NAME="xxx")
              └── case/test_<case>_<nnn>.py::Test<Case>
```

## Src Base Class — Available Methods

The `Src` class is the multi-inheritance root. Accessed via `self.*` in Widget classes.

### AT-SPI (dogtail_utils)

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `self.dog.find_element_by_attr(name)` | `name`: element attribute name | Element object | Find element by AT-SPI accessible name |
| `self.dog.element_click(name)` | `name`: element name | None | Click element by name |
| `self.dog.element_right_click(name)` | `name`: element name | None | Right-click element |
| `self.dog.element_double_click(name)` | `name`: element name | None | Double-click element |
| `self.dog.element_input(name, text)` | `name`: element name, `text`: input content | None | Type text into element |
| `self.dog.element_get_text(name)` | `name`: element name | str | Get element text content |
| `self.dog.is_element_exist(name)` | `name`: element name | bool | Check if element exists |
| `self.dog.wait_for_element(name, timeout=5)` | `name`: element name, `timeout`: seconds | Element | Wait for element to appear |

### OCR (ocr_utils)

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `self.ocr(*target_strings, similarity=0.6, return_first=True, lang="ch")` | strings to search, match threshold | (x, y) or None | Find text position on screen |
| `self.ocr_in_window_by_ui(*target_strings, **kwargs)` | strings to search | (x, y) or raises | Find text in app window (uses ui.ini) |
| `self.click_by_ocr(*target_strings, **kwargs)` | strings to search | bool | Click text on screen |
| `self.right_click_by_ocr(*target_strings, **kwargs)` | strings | bool | Right-click text on screen |

### Image Recognition (image_utils)

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `self.find_image(*elements, rate=0.9)` | image paths, match threshold | (x, y) tuple | Locate image on screen |
| `self.image_click(*elements, rate=0.9)` | image paths, match threshold | None | Click image on screen |
| `self.find_image_in_widget(*elements, **kwargs)` | image paths, window rect | (x, y) | Locate image within window |
| `self.save_temporary_picture(x, y, w, h)` | capture region | temp file path | Screenshot region |

### Input (mouse_key)

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `self.click(x, y)` | screen coordinates | None | Left-click |
| `self.right_click(x, y)` | screen coordinates | None | Right-click |
| `self.double_click(x, y)` | screen coordinates | None | Double-click |
| `self.input_message(text)` | text to type | None | Simulate keyboard typing |
| `self.hot_key(keys)` | key combo e.g. "ctrl+c" | None | Press key combination |
| `self.press_key(key)` | single key e.g. "Return" | None | Press single key |

### ButtonCenter (ui.ini coordinate system)

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `self.ui.btn_size(name)` | section name in ui.ini | (x, y, w, h) | Get button rectangle |
| `self.ui.btn_center(name)` | section name | (x, y) | Get button center coordinates |

## Assertion Methods (from AssertCommon)

All available via `self.assert_*` in test case classes.

| Method | Parameters | Description |
|--------|-----------|-------------|
| `assert_true(expect)` | `expect`: bool | Assert value is True |
| `assert_false(expect)` | `expect`: bool | Assert value is False |
| `assert_equal(expect, actual)` | expected, actual values | Assert two values equal |
| `assert_not_equal(expect, actual)` | expected, actual | Assert two values differ |
| `assert_process_status(expect, app)` | True/False, process name | Assert process is/isn't running |
| `assert_process_num(num, app)` | expected count, process name | Assert N instances running |
| `assert_window_amount(app, expect)` | app name, expected count | Assert window count |
| `assert_window_size(expect, real)` | expected, actual (w,h) tuples | Assert window dimensions |
| `assert_element_exist(expr)` | AT-SPI path expression | Assert element exists |
| `assert_element_not_exist(expr)` | AT-SPI path expression | Assert element does not exist |
| `assert_element_numbers(expr, number)` | AT-SPI path, expected count | Assert count of matching elements |
| `assert_ocr_exist(*strings, **kwargs)` | strings to search | Assert text found via OCR |
| `assert_ocr_not_exist(*strings, **kwargs)` | strings | Assert text NOT found |
| `assert_image_exist(image, rate=0.9)` | image path, match rate | Assert image on screen |
| `assert_image_not_exist(image, rate=0.9)` | image path, match rate | Assert image NOT on screen |
| `assert_file_exist(widget, file)` | widget obj or None, file path | Assert file exists |
| `assert_file_not_exist(widget, file)` | widget obj, file path | Assert file absent |
| `assert_theme(expect)` | "light" or "dark" | Assert system theme |
| `assert_share_folder(filename)` | filename | Assert Samba share exists |
| `assert_not_share_folder(filename)` | filename | Assert Samba share absent |

## Widget Method Naming Conventions

| Pattern | Example | When to Use |
|---------|---------|-------------|
| `click_<target>_by_attr()` | `click_play_by_attr()` | AT-SPI element click |
| `click_<target>_by_image()` | `click_save_by_image()` | Image recognition click |
| `click_<target>_by_ocr()` | `click_confirm_by_ocr()` | OCR text click |
| `click_<target>_by_ui()` | `click_menu_by_ui()` | ButtonCenter coordinate click |
| `get_<target>_text()` | `get_title_text()` | Read element text |
| `get_<target>_position()` | `get_window_position()` | Read screen coordinates |
| `input_<target>_text()` | `input_search_text("text")` | Type into input field |
| `input_<target>_text_by_attr()` | `input_url_by_attr("url")` | AT-SPI input targeting |
| `switch_<target>()` | `switch_dark_mode()` | Toggle switch/checkbox |
| `select_<target>(item)` | `select_language("中文")` | Select from dropdown/list |
| `wait_<target>(timeout=5)` | `wait_dialog(timeout=10)` | Wait for element to appear |
| `verify_<target>()` | `verify_page_loaded()` | Check state, return bool |

## Common Operation Patterns

### DTK Main Menu

```python
def click_about_in_menu(self):
    """Open About dialog via Help menu."""
    self.dog.element_click("主菜单")  # Open main menu
    self.dog.element_click("关于")    # Click About item

# Or using hot_key:
def click_settings_in_menu(self):
    self.hot_key("alt+s")  # Direct keyboard shortcut
```

### Dialog Interaction

```python
def close_dialog_by_attr(self):
    """Close a dialog by clicking the close button."""
    if self.dog.is_element_exist("Btn_关闭"):
        self.dog.element_click("Btn_关闭")

def confirm_dialog(self):
    """Click OK in a confirmation dialog."""
    self.dog.element_click("确定")
```

### File Dialog (Open/Save)

```python
def open_file_by_path(self, filepath):
    """Open file via file dialog keyboard navigation."""
    self.dog.element_click("Btn_打开文件")
    import time; time.sleep(0.5)
    self.hot_key("ctrl+l")  # Focus path bar
    self.input_message(filepath)
    self.press_key("Return")
    time.sleep(0.5)
```

### Search/Filter

```python
def search_by_attr(self, keyword):
    """Type into search box and press Enter."""
    self.dog.element_input("Edt_搜索", keyword)
    self.press_key("Return")
```

### Tab/Section Navigation

```python
def switch_to_tab_by_attr(self, tab_name):
    """Click tab by its display name."""
    self.dog.element_click(tab_name)
```

### Scroll Within List/View

```python
def scroll_down_in_view(self):
    """Scroll down in main view area."""
    # Get view center, then scroll
    _x, _y = self.ui.btn_center("主视图区域")
    self.click(_x, _y)  # Focus the view first
    self.mouse_key.scroll(-3)  # Negative = scroll down
```
