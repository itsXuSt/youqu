# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for src.web_spec.action_executor."""

from web_spec.action_executor import execute
from web_spec.models import ActionSpec


class FakeKeyboard:
    def __init__(self):
        self.typed = ""
        self.pressed = ""

    def type(self, value):
        self.typed = value

    def press(self, value):
        self.pressed = value


class FakePage:
    def __init__(self):
        self.keyboard = FakeKeyboard()


def test_keyboard_type_action():
    page = FakePage()
    spec = ActionSpec.model_validate({"type": "keyboard_type", "value": "hello"})

    result = execute(page, spec)

    assert result.success is True
    assert page.keyboard.typed == "hello"


def test_press_key_requires_key():
    result = execute(FakePage(), ActionSpec.model_validate({"type": "press_key"}))

    assert result.success is False
    assert "key" in result.error
