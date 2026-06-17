# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Execute deterministic Web spec assertions with retry."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from web_spec.locator_resolver import LocatorError, ResolvedLocator, resolve, resolve_all, resolve_lazy
from web_spec.models import AssertionSpec, AssertionType, ExecutionSpec


@dataclass
class AssertionResult:
    """Single assertion execution result."""

    type: str
    success: bool
    expected: Any = None
    actual: Any = None
    error: str | None = None
    locator_strategy: str | None = None
    locator_value: str | None = None
    locator_match_count: int = 0
    locator_stability: str | None = None
    duration_ms: int = 0
    retry_count: int = 0


class AssertionEvaluationError(AssertionError):
    """Assertion failure with actual value and locator metadata."""

    def __init__(self, message: str, actual: Any = None, resolved: ResolvedLocator | None = None):
        super().__init__(message)
        self.actual = actual
        self.resolved = resolved


def execute(page: Any, spec: AssertionSpec, execution: ExecutionSpec | None = None) -> AssertionResult:
    """Execute one assertion, retrying until timeout when enabled."""
    start = time.monotonic()
    timeout_ms = spec.timeout_ms or (execution.assertion_timeout_ms if execution else 30000)
    retry_interval_ms = execution.assertion_retry_interval_ms if execution else 500
    retry_enabled = spec.retry and (execution.assertion_retry if execution else True)
    deadline = start + timeout_ms / 1000
    retry_count = 0
    last_error = ""
    last_actual = None
    last_resolved = None

    while True:
        try:
            actual, resolved = _evaluate(page, spec)
            return _make_result(spec, True, start, actual=actual, resolved=resolved, retry_count=retry_count)
        except AssertionEvaluationError as exc:
            last_error = str(exc)
            last_actual = exc.actual
            last_resolved = exc.resolved
        except (AssertionError, LocatorError) as exc:
            last_error = str(exc)
            last_actual = None
            last_resolved = None
        now = time.monotonic()
        if retry_enabled and now < deadline:
            retry_count += 1
            time.sleep(min(retry_interval_ms / 1000, max(deadline - now, 0)))
            continue
        break

    return _make_result(
        spec,
        False,
        start,
        actual=last_actual,
        error=last_error,
        resolved=last_resolved,
        retry_count=retry_count,
    )


def _evaluate(page: Any, spec: AssertionSpec) -> tuple[Any, ResolvedLocator | None]:
    if spec.type == AssertionType.VISIBLE:
        resolved = _require_locator(page, spec)
        actual = "visible" if resolved.locator.is_visible() else "not_visible"
        if actual != "visible":
            _fail("元素不可见", actual, resolved)
        return actual, resolved
    if spec.type == AssertionType.NOT_VISIBLE:
        if not spec.locator:
            raise AssertionError("not_visible 需要 locator")
        resolved = resolve_lazy(page, spec.locator)
        actual = "visible" if resolved.locator.count() > 0 and resolved.locator.is_visible() else "not_visible"
        if actual == "visible":
            _fail("元素意外可见", actual, resolved)
        return actual, resolved
    if spec.type == AssertionType.TEXT_CONTAINS:
        resolved = _require_locator(page, spec)
        actual = resolved.locator.text_content() or ""
        expected_items = _expected_list(spec.expected)
        missing = [item for item in expected_items if item not in actual]
        if missing:
            _fail(f"文本不包含 {missing}: 实际='{actual}'", actual, resolved)
        return actual, resolved
    if spec.type == AssertionType.TEXT_EQUALS:
        resolved = _require_locator(page, spec)
        actual = resolved.locator.text_content() or ""
        expected = str(spec.expected)
        if actual != expected:
            _fail(f"文本不匹配: 期望='{expected}', 实际='{actual}'", actual, resolved)
        return actual, resolved
    if spec.type == AssertionType.HTML_CONTAINS:
        resolved = _require_locator(page, spec)
        actual = resolved.locator.inner_html() or ""
        missing = [item for item in _expected_list(spec.expected) if item not in actual]
        if missing:
            _fail(f"HTML 不包含 {missing}: 实际='{actual}'", actual, resolved)
        return actual, resolved
    if spec.type == AssertionType.HTML_EQUALS:
        resolved = _require_locator(page, spec)
        actual = resolved.locator.inner_html() or ""
        expected = str(spec.expected)
        if actual != expected:
            _fail(f"HTML 不匹配: 期望='{expected}', 实际='{actual}'", actual, resolved)
        return actual, resolved
    if spec.type == AssertionType.ENABLED:
        resolved = _require_locator(page, spec)
        actual = "enabled" if resolved.locator.is_enabled() else "disabled"
        if actual != "enabled":
            _fail("元素不可用", actual, resolved)
        return actual, resolved
    if spec.type == AssertionType.DISABLED:
        resolved = _require_locator(page, spec)
        actual = "enabled" if resolved.locator.is_enabled() else "disabled"
        if actual == "enabled":
            _fail("元素意外可用", actual, resolved)
        return actual, resolved
    if spec.type == AssertionType.COUNT:
        resolved = _require_locator(page, spec)
        actual = resolved.match_count
        expected = int(spec.expected)
        if actual != expected:
            _fail(f"元素数量不匹配: 期望={expected}, 实际={actual}", actual, resolved)
        return actual, resolved
    if spec.type == AssertionType.INPUT_VALUE_EQUALS:
        resolved = _require_locator(page, spec)
        actual = resolved.locator.input_value() or ""
        expected = str(spec.expected)
        if actual != expected:
            _fail(f"输入值不匹配: 期望='{expected}', 实际='{actual}'", actual, resolved)
        return actual, resolved
    if spec.type == AssertionType.INPUT_VALUE_CONTAINS:
        resolved = _require_locator(page, spec)
        actual = resolved.locator.input_value() or ""
        missing = [item for item in _expected_list(spec.expected) if item not in actual]
        if missing:
            _fail(f"输入值不包含 {missing}: 实际='{actual}'", actual, resolved)
        return actual, resolved
    if spec.type == AssertionType.ATTRIBUTE_EQUALS:
        resolved = _require_locator(page, spec)
        attribute = _require_attribute(spec)
        actual = resolved.locator.get_attribute(attribute) or ""
        expected = str(spec.expected)
        if actual != expected:
            _fail(f"属性 {attribute} 不匹配: 期望='{expected}', 实际='{actual}'", actual, resolved)
        return actual, resolved
    if spec.type == AssertionType.ATTRIBUTE_CONTAINS:
        resolved = _require_locator(page, spec)
        attribute = _require_attribute(spec)
        actual = resolved.locator.get_attribute(attribute) or ""
        missing = [item for item in _expected_list(spec.expected) if item not in actual]
        if missing:
            _fail(f"属性 {attribute} 不包含 {missing}: 实际='{actual}'", actual, resolved)
        return actual, resolved
    if spec.type == AssertionType.CLASS_CONTAINS:
        resolved = _require_locator(page, spec)
        actual = resolved.locator.get_attribute("class") or ""
        missing = [item for item in _expected_list(spec.expected) if item not in actual]
        if missing:
            _fail(f"class 不包含 {missing}: 实际='{actual}'", actual, resolved)
        return actual, resolved
    if spec.type == AssertionType.URL_EQUALS:
        actual = page.url
        expected = str(spec.expected)
        if actual != expected:
            _fail(f"URL 不匹配: 期望='{expected}', 实际='{actual}'", actual, None)
        return actual, None
    if spec.type == AssertionType.URL_CONTAINS:
        actual = page.url
        missing = [item for item in _expected_list(spec.expected) if item not in actual]
        if missing:
            _fail(f"URL 不包含 {missing}: 实际='{actual}'", actual, None)
        return actual, None
    if spec.type == AssertionType.TEXT_SEQUENCE:
        if not spec.locator:
            raise AssertionError("text_sequence 需要 locator")
        resolved = resolve_all(page, spec.locator)
        actual = [str(item).strip() for item in resolved.locator.all_text_contents()]
        expected = _expected_list(spec.expected)
        mode = spec.mode or "equals"
        if mode == "contains_order":
            if not _contains_order(actual, expected):
                _fail(f"文本序列未按顺序包含期望: 期望={expected}, 实际={actual}", actual, resolved)
        elif actual != expected:
            _fail(f"文本序列不匹配: 期望={expected}, 实际={actual}", actual, resolved)
        return actual, resolved
    raise AssertionError(f"不支持的 assertion type: {spec.type}")


def _require_locator(page: Any, spec: AssertionSpec) -> ResolvedLocator:
    if not spec.locator:
        raise AssertionError(f"{spec.type.value} 需要 locator")
    return resolve(page, spec.locator, require_unique=False)


def _require_attribute(spec: AssertionSpec) -> str:
    if not spec.attribute:
        raise AssertionError(f"{spec.type.value} 需要 attribute")
    return spec.attribute


def _expected_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _contains_order(actual: list[str], expected: list[str]) -> bool:
    start = 0
    for expected_item in expected:
        for index in range(start, len(actual)):
            if expected_item in actual[index]:
                start = index + 1
                break
        else:
            return False
    return True


def _fail(message: str, actual: Any, resolved: ResolvedLocator | None) -> None:
    raise AssertionEvaluationError(message, actual=actual, resolved=resolved)


def _make_result(
    spec: AssertionSpec,
    success: bool,
    start: float,
    actual: Any = None,
    error: str | None = None,
    resolved: ResolvedLocator | None = None,
    retry_count: int = 0,
) -> AssertionResult:
    return AssertionResult(
        type=spec.type.value,
        success=success,
        expected=spec.expected,
        actual=actual,
        error=error,
        locator_strategy=resolved.strategy if resolved else (spec.locator.strategy.value if spec.locator else None),
        locator_value=resolved.value if resolved else (spec.locator.value if spec.locator else None),
        locator_match_count=resolved.match_count if resolved else 0,
        locator_stability=resolved.stability if resolved else (spec.locator.stability if spec.locator else None),
        duration_ms=int((time.monotonic() - start) * 1000),
        retry_count=retry_count,
    )
