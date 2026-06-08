# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""YAML assert type dispatch to AssertCommon methods.

Maps YAML assert type strings to AssertCommon method calls.
Each handler raises AssertionError on failure.
"""

from __future__ import annotations

from typing import Any, Callable

from src.yaml_test.executor import selector_to_expr
from src.yaml_test.parser import AssertStep
from src.yaml_test.elements import resolve_ref

# Module-level elements cache, set by run_assert before dispatching
_ELEMENTS: dict | None = None


def _resolve_expr(step: AssertStep) -> str:
    """Build a YouQu expr from the assert step's selector, expr, or ref field."""
    if step.expr:
        return step.expr
    if step.ref and _ELEMENTS:
        attrs = resolve_ref(step.ref, _ELEMENTS)
        return selector_to_expr(attrs)
    if step.selector is not None:
        return selector_to_expr(step.selector.model_dump(exclude_none=True))
    return ""


def _assert_element_visible(step: AssertStep) -> None:
    from src.assert_common import AssertCommon

    AssertCommon.assert_element_exist(_resolve_expr(step))


def _assert_element_not_visible(step: AssertStep) -> None:
    from src.assert_common import AssertCommon

    AssertCommon.assert_element_not_exist(_resolve_expr(step))


def _assert_element_numbers(step: AssertStep) -> None:
    from src.assert_common import AssertCommon

    n = step.number if step.number is not None else int(step.value or 0)
    AssertCommon.assert_element_numbers(_resolve_expr(step), n)


def _assert_element_text(step: AssertStep) -> None:
    from src.dogtail_utils import DogtailUtils

    expr = _resolve_expr(step)
    element = DogtailUtils().find_element_by_attr(expr)
    actual = getattr(element, "name", "") or ""
    expected = str(step.expected or "")
    if expected not in actual:
        raise AssertionError(
            f"Element text '{actual}' does not contain '{expected}'"
        )


def _assert_process_running(step: AssertStep) -> None:
    from src.assert_common import AssertCommon

    app = step.app or step.value or ""
    AssertCommon.assert_process_status(True, app)


def _assert_process_not_running(step: AssertStep) -> None:
    from src.assert_common import AssertCommon

    app = step.app or step.value or ""
    AssertCommon.assert_process_status(False, app)


def _assert_file_exists(step: AssertStep) -> None:
    from src.assert_common import AssertCommon

    path = step.path or step.value or ""
    AssertCommon.assert_file_exist(path)


def _assert_file_not_exists(step: AssertStep) -> None:
    from src.assert_common import AssertCommon

    path = step.path or step.value or ""
    AssertCommon.assert_file_not_exist(path)


def _assert_image_exist(step: AssertStep) -> None:
    from src.assert_common import AssertCommon

    path = step.path or step.value or ""
    AssertCommon.assert_image_exist(path)


def _assert_image_not_exist(step: AssertStep) -> None:
    from src.assert_common import AssertCommon

    path = step.path or step.value or ""
    AssertCommon.assert_image_not_exist(path)


def _assert_ocr_exist(step: AssertStep) -> None:
    from src.assert_common import AssertCommon

    text = step.value or step.expected or ""
    AssertCommon.assert_ocr_exist(str(text))


def _assert_ocr_not_exist(step: AssertStep) -> None:
    from src.assert_common import AssertCommon

    text = step.value or step.expected or ""
    AssertCommon.assert_ocr_not_exist(str(text))


def _assert_window_size(step: AssertStep) -> None:
    from src.assert_common import AssertCommon

    expected = step.expected
    actual = step.value
    AssertCommon.assert_window_size(expected, actual)


def _assert_window_amount(step: AssertStep) -> None:
    from src.assert_common import AssertCommon

    app = step.app or ""
    n = step.number if step.number is not None else int(step.value or 0)
    AssertCommon.assert_window_amount(app, n)


def _assert_dbus_property(step: AssertStep) -> None:
    from src.dbus_utils import DbusUtils

    value_dict = step.value if isinstance(step.value, dict) else {}
    dbus_name = value_dict.get("dbus_name", "")
    object_path = value_dict.get("object_path", "")
    interface = value_dict.get("interface", "")
    prop = value_dict.get("property", "")
    bus_type = value_dict.get("bus_type", "session")

    dog = DbusUtils(dbus_name, object_path, interface)
    if bus_type == "system":
        actual = dog.get_system_properties_value(prop)
    else:
        actual = dog.get_session_properties_value(prop)
    if step.expected is not None and actual != step.expected:
        raise AssertionError(
            f"DBus property '{prop}': expected {step.expected}, got {actual}"
        )


ASSERT_HANDLERS: dict[str, Callable[[AssertStep], None]] = {
    "element_visible": _assert_element_visible,
    "element_not_visible": _assert_element_not_visible,
    "element_numbers": _assert_element_numbers,
    "element_text": _assert_element_text,
    "process_running": _assert_process_running,
    "process_not_running": _assert_process_not_running,
    "file_exists": _assert_file_exists,
    "file_not_exists": _assert_file_not_exists,
    "image_exist": _assert_image_exist,
    "image_not_exist": _assert_image_not_exist,
    "ocr_exist": _assert_ocr_exist,
    "ocr_not_exist": _assert_ocr_not_exist,
    "window_size": _assert_window_size,
    "window_amount": _assert_window_amount,
    "dbus_property": _assert_dbus_property,
}


def run_assert(assert_step: AssertStep, elements: dict | None = None) -> None:
    """Dispatch an assert step to the appropriate handler.

    Raises:
        ValueError: If assert type is unknown.
        AssertionError: If the assertion fails.
    """
    global _ELEMENTS
    _ELEMENTS = elements
    handler = ASSERT_HANDLERS.get(assert_step.type)
    if handler is None:
        raise ValueError(f"Unknown assert type: {assert_step.type}")
    handler(assert_step)
