# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for src.web_spec.assertion_executor."""

from web_spec.assertion_executor import execute
from web_spec.models import AssertionSpec, ExecutionSpec


class FakeLocator:
    first = None

    def __init__(
        self,
        text="hello",
        count=1,
        input_value="",
        attributes=None,
        texts=None,
        visible=True,
        enabled=True,
    ):
        self.first = self
        self._text = text
        self._count = count
        self._input_value = input_value
        self._attributes = attributes or {}
        self._texts = texts or [text]
        self._visible = visible
        self._enabled = enabled
        self.text_content_calls = 0

    def count(self):
        return self._count

    def is_visible(self):
        return self._visible

    def is_enabled(self):
        return self._enabled

    def text_content(self):
        self.text_content_calls += 1
        return self._text

    def inner_html(self):
        return self._text

    def input_value(self):
        return self._input_value

    def get_attribute(self, name):
        return self._attributes.get(name)

    def all_text_contents(self):
        return self._texts


class FakePage:
    def __init__(self, locators=None, url="http://example.test/chat"):
        self.locators = locators or {}
        self.url = url

    def locator(self, value):
        locator = self.locators.get(value)
        if isinstance(locator, list):
            if locator:
                return locator.pop(0)
            return FakeLocator(text=value, count=0)
        if locator is not None:
            return locator
        locator = FakeLocator(text=value, count=1)
        self.locators[value] = locator
        return locator

    def get_by_text(self, value, exact=False):
        return self.locator(value)

    def get_by_test_id(self, value):
        return self.locator(value)

    def get_by_role(self, value, **options):
        return self.locator(options.get("name") or value)


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


def test_failed_assertion_keeps_actual_value():
    locator = FakeLocator(text="实际文本")
    spec = AssertionSpec.model_validate({
        "type": "text_equals",
        "locator": {"strategy": "css", "value": ".message"},
        "expected": "期望文本",
        "retry": False,
    })

    result = execute(FakePage({".message": locator}), spec)

    assert result.success is False
    assert result.actual == "实际文本"
    assert result.locator_match_count == 1


def test_retry_failure_clears_stale_actual_when_last_attempt_has_no_locator():
    spec = AssertionSpec.model_validate({
        "type": "text_equals",
        "locator": {"strategy": "css", "value": ".message"},
        "expected": "完成",
        "timeout_ms": 1,
        "retry": True,
    })
    page = FakePage({".message": [FakeLocator(text="加载中"), FakeLocator(count=0)]})
    execution = ExecutionSpec(assertion_retry=True, assertion_retry_interval_ms=1)

    result = execute(page, spec, execution)

    assert result.success is False
    assert result.actual is None
    assert result.locator_match_count == 0
    assert "匹配 0 个元素" in result.error


def test_execution_assertion_retry_can_disable_retry():
    locator = FakeLocator(text="实际文本")
    spec = AssertionSpec.model_validate({
        "type": "text_equals",
        "locator": {"strategy": "css", "value": ".message"},
        "expected": "期望文本",
        "retry": True,
        "timeout_ms": 50,
    })
    execution = ExecutionSpec(assertion_retry=False, assertion_retry_interval_ms=1)

    result = execute(FakePage({".message": locator}), spec, execution)

    assert result.success is False
    assert result.retry_count == 0
    assert locator.text_content_calls == 1


def test_input_value_assertions():
    locator = FakeLocator(input_value="hello YouQu")
    page = FakePage({"input": locator})

    equals = execute(page, AssertionSpec.model_validate({
        "type": "input_value_equals",
        "locator": {"strategy": "css", "value": "input"},
        "expected": "hello YouQu",
        "retry": False,
    }))
    contains = execute(page, AssertionSpec.model_validate({
        "type": "input_value_contains",
        "locator": {"strategy": "css", "value": "input"},
        "expected": "YouQu",
        "retry": False,
    }))

    assert equals.success is True
    assert contains.success is True
    assert contains.actual == "hello YouQu"


def test_attribute_and_class_assertions():
    locator = FakeLocator(attributes={"aria-label": "提交按钮", "class": "btn primary"})
    page = FakePage({"button": locator})

    attr_equals = execute(page, AssertionSpec.model_validate({
        "type": "attribute_equals",
        "locator": {"strategy": "css", "value": "button"},
        "attribute": "aria-label",
        "expected": "提交按钮",
        "retry": False,
    }))
    attr_contains = execute(page, AssertionSpec.model_validate({
        "type": "attribute_contains",
        "locator": {"strategy": "css", "value": "button"},
        "attribute": "aria-label",
        "expected": "提交",
        "retry": False,
    }))
    class_contains = execute(page, AssertionSpec.model_validate({
        "type": "class_contains",
        "locator": {"strategy": "css", "value": "button"},
        "expected": "primary",
        "retry": False,
    }))

    assert attr_equals.success is True
    assert attr_contains.success is True
    assert class_contains.success is True


def test_attribute_assertion_requires_attribute_name():
    spec = AssertionSpec.model_validate({
        "type": "attribute_equals",
        "locator": {"strategy": "css", "value": "button"},
        "expected": "提交按钮",
        "retry": False,
    })

    result = execute(FakePage(), spec)

    assert result.success is False
    assert "attribute" in result.error


def test_url_assertions_do_not_require_locator():
    page = FakePage(url="http://example.test/chat/123")

    equals = execute(page, AssertionSpec.model_validate({
        "type": "url_equals",
        "expected": "http://example.test/chat/123",
        "retry": False,
    }))
    contains = execute(page, AssertionSpec.model_validate({
        "type": "url_contains",
        "expected": "/chat/",
        "retry": False,
    }))

    assert equals.success is True
    assert contains.success is True


def test_text_sequence_assertion_equals():
    locator = FakeLocator(count=3, texts=["写作", "翻译", "总结"])
    spec = AssertionSpec.model_validate({
        "type": "text_sequence",
        "locator": {"strategy": "css", "value": ".assistant-item"},
        "expected": ["写作", "翻译", "总结"],
        "retry": False,
    })

    result = execute(FakePage({".assistant-item": locator}), spec)

    assert result.success is True
    assert result.actual == ["写作", "翻译", "总结"]
    assert result.locator_match_count == 3


def test_text_sequence_assertion_contains_order():
    locator = FakeLocator(count=4, texts=["第一个：写作", "其他", "第二个：翻译", "第三个：总结"])
    spec = AssertionSpec.model_validate({
        "type": "text_sequence",
        "locator": {"strategy": "css", "value": ".assistant-item"},
        "expected": ["写作", "翻译", "总结"],
        "mode": "contains_order",
        "retry": False,
    })

    result = execute(FakePage({".assistant-item": locator}), spec)

    assert result.success is True
