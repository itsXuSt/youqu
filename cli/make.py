# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only

from pathlib import Path

_PYTEST_INI = """\
[pytest]
addopts = -s -vv --no-header --tb=auto -r fEs --color=auto
testpaths = case
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


def _snake_to_camel(name):
    return "".join(word.capitalize() for word in name.split("_"))


def _write(target, rel_path, content):
    full = target / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")


def generate(name, output_dir="."):
    target = Path(output_dir).resolve() / "autotest"
    if target.exists():
        print(f"autotest/ already exists in {output_dir}")
        return

    camel = _snake_to_camel(name)

    (target / "case").mkdir(parents=True, exist_ok=True)
    (target / "widget" / "pic_res").mkdir(parents=True, exist_ok=True)
    (target / "report").mkdir(parents=True, exist_ok=True)

    _write(target, "pytest.ini", _PYTEST_INI)
    _write(target, "conftest.py", _CONFTEST_PY)
    _write(target, "config.ini", _CONFIG_INI)
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

    print(f"Generated autotest/ in {target}")
    print(f"  App: {name}")
    print(f"  Usage: cd {target.parent} && youqu run")
