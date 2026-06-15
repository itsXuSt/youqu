# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for src.web_spec.assertion_executor."""

from web_spec.assertion_executor import execute
from web_spec.models import AssertionSpec


class FakeLocator:
    first = None

    def __init__(self, text="hello", count=1):
        self.first = self
        self._text = text
        self._count = count

    def count(self):
        return self._count

    def is_visible(self):
        return True

    def text_content(self):
        return self._text


class FakePage:
    def get_by_text(self, value, exact=False):
        return FakeLocator(text=value, count=1)


def test_text_contains_assertion_passes():
    spec = AssertionSpec.model_validate({
        "type": "text_contains",
        "locator": {"strategy": "text", "value": "hello world"},
        "expected": "world",
        "retry": False,
    })

    result = execute(FakePage(), spec)

    assert result.success is True
    assert result.actual == "hello world"
