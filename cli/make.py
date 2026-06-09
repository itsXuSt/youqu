# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only

from pathlib import Path

_PYTEST_INI_YAML = """\
[pytest]
addopts = -s -vv --no-header --tb=auto -r fEs --color=auto
testpaths = yaml
yaml_files = yaml
minversion = 6.2.5
"""

_PYTEST_INI_PY = """\
[pytest]
addopts = -s -vv --no-header --tb=auto -r fEs --color=auto
testpaths = case
minversion = 6.2.5
"""

_PYTEST_INI_ALL = """\
[pytest]
addopts = -s -vv --no-header --tb=auto -r fEs --color=auto
testpaths = case yaml
yaml_files = yaml
minversion = 6.2.5
"""

_CONFTEST_PY = """\
# autotest conftest
# App-specific fixtures go here.
"""

_CONFIG_INI = """\
[config]
"""

_UI_INI = """\
[window]
direction = center
location = 0, 0, 0, 0
"""

_BASE_CASE = """\
from src.assert_common import AssertCommon


class BaseCase(AssertCommon):

    APP_NAME = "{name}"
"""

_BASE_WIDGET = """\
from os.path import dirname, abspath, join

from src import Src
from src import log


class BaseWidget(Src):

    _BASE = dirname(dirname(abspath(__file__)))
    UI_INI_PATH = join(_BASE, "ui.ini")
    PIC_RES_PATH = join(_BASE, "widget", "pic_res")

    APP_NAME = "{name}"
    DESC = "/usr/bin/{name}"

    def __init__(self, number=-1, check_start=True):
        kwargs = dict(
            name=self.APP_NAME,
            description=self.DESC,
            check_start=check_start,
            config_path=self.UI_INI_PATH,
        )
        if number > 0:
            kwargs["number"] = number
        Src.__init__(self, **kwargs)

    def find_image_in_screen(self, *elements, rate=0.9, picture_abspath=None):
        paths = tuple(f"{{self.PIC_RES_PATH}}/{{x}}" for x in elements)
        return self.find_image(*paths, rate=rate, picture_abspath=picture_abspath)
"""

_APP_WIDGET = """\
from .base_widget import BaseWidget
from src import log


@log
class {camel}Widget(BaseWidget):
    pass
"""

_SAMPLE_TEST = """\
from .base_case import BaseCase
from widget import {camel}Widget


class Test{camel}(BaseCase):

    def test_{name}_001(self):
        pass
"""

_SAMPLE_YAML = r"""# YAML test case for {name}
#
# Executed via youqu run — collected by pytest and dispatched to YouQu framework APIs.
# All element references use 'ref' to look up entries in elements.yaml.
#
# Actions supported: session_start, session_stop, keyboard_press, keyboard_hot_key,
#   keyboard_type, mouse_click, mouse_right_click, mouse_double_click, mouse_scroll,
#   mouse_drag, element_action, element_set_value, main_menu_comb, context_menu_comb,
#   dbus_call, dbus_get_property, wait, screenshot
# Asserts supported: element_visible, element_not_visible, element_numbers,
#   element_text, process_running, process_not_running, file_exists, file_not_exists,
#   image_exist, image_not_exist, ocr_exist, ocr_not_exist, window_size, dbus_property

name: "{name} 基础启动测试"
description: |
  前置条件:

  测试步骤:
  1.

  预期结果:
  1.
module: ""
feature: ""
tags: []
app: "{name}"
screenshot: false

setup:
  - action: session_start
    command: "{name}"
    wait: 3.0

steps:
  - name: "验证主窗口可见"
    action: element_action
    ref: main_frame
    do: "click"
    assert:
      - type: element_visible
        selector:
          role: "frame"

  - name: "验证进程运行中"
    assert:
      - type: process_running
        app: "{name}"

teardown:
  - action: session_stop
"""

_ELEMENTS_YAML = """# Element registry for {name}
#
# This is the MANDATORY, single-source-of-truth registry for UI element
# references used in YAML test cases.  Every ``ref`` in ``test_*.yaml``
# must have a matching entry here.
#
# Each entry maps a logical alias to one or more of:
#   name           — AT-SPI accessible name (preferred for selection)
#   role           — AT-SPI role (e.g. "frame", "push button", "menu item")
#   x, y           — screen coordinates (for mouse click / right-click)
#   menu           — list of menu items (for keyboard menu navigation)
#   index          — element index when multiple matches exist (default 0)
#   accessible_id  — AT-SPI accessible ID (rarely needed)
#
# Regenerate by capturing the live AT-SPI tree:
#   youqu mcp → atspi_find_element / atspi_get_children_text

app: {name}
elements:
  main_frame:
    role: "frame"
"""


def _snake_to_camel(name):
    return "".join(word.capitalize() for word in name.split("_"))


def _write(target, rel_path, content):
    full = target / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")


def generate(name, output_dir=".", fmt="yaml"):
    target = Path(output_dir).resolve() / "autotest"
    if target.exists():
        print(f"autotest/ already exists in {output_dir}")
        return

    camel = _snake_to_camel(name)
    want_py = fmt in ("py", "all")
    want_yaml = fmt in ("yaml", "all")

    (target / "report").mkdir(parents=True, exist_ok=True)

    if fmt == "yaml":
        _write(target, "pytest.ini", _PYTEST_INI_YAML)
    elif fmt == "py":
        _write(target, "pytest.ini", _PYTEST_INI_PY)
    else:
        _write(target, "pytest.ini", _PYTEST_INI_ALL)

    _write(target, "conftest.py", _CONFTEST_PY)
    _write(target, "config.ini", _CONFIG_INI)

    if want_py:
        (target / "case").mkdir(parents=True, exist_ok=True)
        (target / "widget" / "pic_res").mkdir(parents=True, exist_ok=True)
        _write(target, "ui.ini", _UI_INI)

        _write(target, "case/__init__.py", "from .base_case import BaseCase\n")
        _write(target, "case/base_case.py", _BASE_CASE.format(name=name))
        _write(
            target,
            f"case/test_{name}_001.py",
            _SAMPLE_TEST.format(name=name, camel=camel),
        )
        _write(
            target,
            "widget/__init__.py",
            f"from .{name}_widget import {camel}Widget\n",
        )
        _write(target, "widget/base_widget.py", _BASE_WIDGET.format(name=name))
        _write(
            target,
            f"widget/{name}_widget.py",
            _APP_WIDGET.format(name=name, camel=camel),
        )
        _write(target, "widget/pic_res/.gitkeep", "")

    if want_yaml:
        (target / "yaml").mkdir(parents=True, exist_ok=True)
        _write(target, "yaml/.gitkeep", "")
        _write(target, "yaml/elements.yaml", _ELEMENTS_YAML.format(name=name))
        _write(target, f"yaml/test_{name}_001.yaml", _SAMPLE_YAML.format(name=name))

    if want_yaml:
        try:
            from src.yaml_test.index import YamlIndex
            yaml_dir = target / "yaml"
            idx = YamlIndex(yaml_dir)
            count = idx.rebuild()
            print(f"  Index: {len(count) if isinstance(count, list) else 0} test(s)")
        except Exception:
            pass

    print(f"Generated autotest/ in {target}")
    print(f"  App: {name}")
    print(f"  Format: {fmt}")
    print(f"  Usage: cd {target.parent} && youqu run")
