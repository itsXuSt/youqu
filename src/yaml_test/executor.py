# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Step executor — dispatches YAML action steps to YouQu API calls.

Converts Selector models to YouQu AT-SPI expr strings, then calls
DogtailUtils, MouseKey, DbusUtils, or MenuNavigator as appropriate.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from src.yaml_test.elements import resolve_ref
from src.yaml_test.parser import ActionStep, TestCase


def selector_to_expr(selector: Any) -> str:
    """Convert a Selector dict or model to a YouQu AT-SPI expr string.

    YouQu expr format: $-prefixed, /-separated, trailing /.
    $/name/ searches root's children for elements matching name.

    >>> selector_to_expr({"name": "OK"})
    '$/OK/'
    >>> selector_to_expr({})
    '$/'
    """
    if selector is None:
        return "$/"

    if hasattr(selector, "model_dump"):
        sel = selector.model_dump(exclude_none=True)
    elif isinstance(selector, dict):
        sel = {k: v for k, v in selector.items() if v is not None}
    else:
        return "$/"

    name = sel.get("name", "")
    if name:
        return f"$/{name}/"
    return "$/"


def _resolve_step_attrs(step: ActionStep, elements: dict) -> dict:
    """Resolve step.ref to element attributes dict, or fallback to legacy fields.

    Priority: ``step.ref`` (looked up in elements.yaml) → inline ``step.selector``,
    ``step.x``, ``step.y``, ``step.items``.  Never mixes the two paths.
    """
    if step.ref:
        attrs = dict(resolve_ref(step.ref, elements))
        if "x" not in attrs:
            attrs.setdefault("x", 0)
        if "y" not in attrs:
            attrs.setdefault("y", 0)
        if "menu" not in attrs:
            attrs.setdefault("menu", [])
        return attrs

    # Legacy fallback — build attrs dict from inline fields
    attrs: dict = {}
    sel = step.selector
    if sel is not None:
        if hasattr(sel, "model_dump"):
            attrs = sel.model_dump(exclude_none=True)
        elif isinstance(sel, dict):
            attrs = {k: v for k, v in sel.items() if v is not None}
    if step.x is not None:
        attrs["x"] = step.x
    if step.y is not None:
        attrs["y"] = step.y
    if step.items is not None:
        attrs["items"] = step.items
    return attrs


@dataclass
class ExecutorResult:
    """Result of executing a TestCase."""

    passed: bool = True
    message: str = ""
    step_index: int = -1
    errors: list[str] = field(default_factory=list)


def _get_mk(context: dict):
    if context.get("mk") is None:
        from src.mouse_key import MouseKey

        context["mk"] = MouseKey()
    return context["mk"]


def _get_dog(context: dict, app: str | None = None):
    if context.get("dog") is None:
        from src.dogtail_utils import DogtailUtils

        context["dog"] = DogtailUtils(app) if app else DogtailUtils()
    return context["dog"]


def _handle_session_start(step: ActionStep, context: dict) -> None:
    cmd = step.command or context.get("app", "")
    if not cmd:
        raise ValueError("session_start requires 'command' or app name")
    proc = subprocess.Popen(cmd, shell=True)
    context["app_process"] = proc
    if step.wait:
        time.sleep(step.wait)


def _handle_session_stop(step: ActionStep, context: dict) -> None:
    app = context.get("app", "")
    if not app:
        return
    subprocess.run(f"pkill -f {app}", shell=True, check=False)
    context.pop("app_process", None)


def _handle_keyboard_press(step: ActionStep, context: dict) -> None:
    mk = _get_mk(context)
    key = step.keys if isinstance(step.keys, str) else str(step.keys or "")
    mk.press_key(key)


def _handle_keyboard_hot_key(step: ActionStep, context: dict) -> None:
    mk = _get_mk(context)
    keys = step.keys
    if isinstance(keys, str):
        key_list = [k.strip() for k in keys.split(",") if k.strip()]
    elif isinstance(keys, list):
        key_list = [str(k) for k in keys]
    else:
        key_list = [str(keys)]
    mk.hot_key(*key_list)


def _handle_keyboard_type(step: ActionStep, context: dict) -> None:
    mk = _get_mk(context)
    mk.input_message(step.text or "")


def _handle_mouse_click(step: ActionStep, context: dict) -> None:
    mk = _get_mk(context)
    attrs = _resolve_step_attrs(step, context.get("elements", {}))
    mk.click(attrs.get("x", 0), attrs.get("y", 0))


def _handle_mouse_right_click(step: ActionStep, context: dict) -> None:
    mk = _get_mk(context)
    attrs = _resolve_step_attrs(step, context.get("elements", {}))
    mk.right_click(attrs.get("x", 0), attrs.get("y", 0))


def _handle_mouse_double_click(step: ActionStep, context: dict) -> None:
    mk = _get_mk(context)
    attrs = _resolve_step_attrs(step, context.get("elements", {}))
    mk.double_click(attrs.get("x", 0), attrs.get("y", 0))


def _handle_mouse_scroll(step: ActionStep, context: dict) -> None:
    mk = _get_mk(context)
    mk.mouse_scroll(step.amount or 0)


def _handle_mouse_drag(step: ActionStep, context: dict) -> None:
    mk = _get_mk(context)
    attrs = _resolve_step_attrs(step, context.get("elements", {}))
    mk.drag_to(attrs.get("x", 0), attrs.get("y", 0))


def _handle_element_action(step: ActionStep, context: dict) -> None:
    app_name = context.get("app") or ""
    dog = _get_dog(context, app_name)
    elements = context.get("elements") or {}

    attrs = _resolve_step_attrs(step, elements)
    name = attrs.get("name", "")
    expr = f"$/{name}/" if name else "$/"
    idx = attrs.get("index", 0)
    element = dog.find_element_by_attr(expr, idx)
    action = step.do or "click"
    if action == "click":
        element.click()
    elif action == "right_click":
        element.click(button=3)
    elif action == "double_click":
        element.doubleClick()
    elif action == "point":
        dog.element_point(element)
    elif action == "focus":
        element.grabFocus()
    else:
        method = getattr(element, action, None)
        if callable(method):
            method()
        else:
            raise ValueError(f"Unknown element action: {action}")


def _handle_element_set_value(step: ActionStep, context: dict) -> None:
    app_name = context.get("app") or ""
    dog = _get_dog(context, app_name)
    mk = _get_mk(context)
    elements = context.get("elements") or {}

    attrs = _resolve_step_attrs(step, elements)
    name = attrs.get("name", "")
    expr = f"$/{name}/" if name else "$/"
    element = dog.find_element_by_attr(expr)
    element.click()
    mk.input_message(step.text or "")


def _handle_main_menu_comb(step: ActionStep, context: dict) -> None:
    try:
        from src.menu_nav import MenuNavigator
    except ImportError as e:
        raise ImportError(f"menu_nav module not available: {e}") from e

    elements = context.get("elements") or {}
    attrs = _resolve_step_attrs(step, elements)
    items = attrs.get("menu", []) or attrs.get("items", [])

    nav = MenuNavigator(context.get("app"))
    nav.open_main_menu()
    nav.select(items)


def _handle_context_menu_comb(step: ActionStep, context: dict) -> None:
    try:
        from src.menu_nav import MenuNavigator
    except ImportError as e:
        raise ImportError(f"menu_nav module not available: {e}") from e

    elements = context.get("elements") or {}
    attrs = _resolve_step_attrs(step, elements)
    x = attrs.get("x", 0)
    y = attrs.get("y", 0)
    items = attrs.get("menu", []) or attrs.get("items", [])

    nav = MenuNavigator(context.get("app"))
    nav.open_context_menu(x, y)
    nav.select(items)


def _handle_dbus_call(step: ActionStep, context: dict) -> None:
    from src.dbus_utils import DbusUtils

    v = step.value if isinstance(step.value, dict) else {}
    dog = DbusUtils(
        v.get("dbus_name", ""),
        v.get("object_path", ""),
        v.get("interface", ""),
    )
    bus_type = v.get("bus_type", "session")
    if bus_type == "system":
        methods = dog.system_object_methods()
    else:
        methods = dog.session_object_methods()
    method_name = v.get("method", "")
    args = v.get("args", [])
    method = getattr(methods, method_name, None)
    if callable(method):
        method(*args)
    else:
        raise ValueError(f"Unknown DBus method: {method_name}")


def _handle_dbus_get_property(step: ActionStep, context: dict) -> None:
    from src.dbus_utils import DbusUtils

    v = step.value if isinstance(step.value, dict) else {}
    dog = DbusUtils(
        v.get("dbus_name", ""),
        v.get("object_path", ""),
        v.get("interface", ""),
    )
    prop = v.get("property", "")
    bus_type = v.get("bus_type", "session")
    if bus_type == "system":
        dog.get_system_properties_value(prop)
    else:
        dog.get_session_properties_value(prop)


def _handle_wait(step: ActionStep, context: dict) -> None:
    seconds = step.wait if step.wait is not None else 0.0
    time.sleep(seconds)


def _handle_screenshot(step: ActionStep, context: dict) -> None:
    from src.image_utils import ImageUtils

    try:
        mk = _get_mk(context)
        w, h = mk.screen_size()
    except Exception:
        w, h = 1920, 1080
    ImageUtils.save_temporary_picture(0, 0, w, h)


ACTION_HANDLERS: dict[str, Callable[[ActionStep, dict], None]] = {
    "session_start": _handle_session_start,
    "session_stop": _handle_session_stop,
    "keyboard_press": _handle_keyboard_press,
    "keyboard_hot_key": _handle_keyboard_hot_key,
    "keyboard_type": _handle_keyboard_type,
    "mouse_click": _handle_mouse_click,
    "mouse_right_click": _handle_mouse_right_click,
    "mouse_double_click": _handle_mouse_double_click,
    "mouse_scroll": _handle_mouse_scroll,
    "mouse_drag": _handle_mouse_drag,
    "element_action": _handle_element_action,
    "element_set_value": _handle_element_set_value,
    "main_menu_comb": _handle_main_menu_comb,
    "context_menu_comb": _handle_context_menu_comb,
    "dbus_call": _handle_dbus_call,
    "dbus_get_property": _handle_dbus_get_property,
    "wait": _handle_wait,
    "screenshot": _handle_screenshot,
}


class StepExecutor:
    """Executes a parsed TestCase through the YouQu API."""

    def __init__(self, testcase: TestCase):
        self.testcase = testcase
        self.context: dict[str, Any] = {
            "app": testcase.app,
            "mk": None,
            "dog": None,
            "app_process": None,
            "elements": testcase.elements,
        }

    def run(self) -> ExecutorResult:
        """Execute setup → steps → teardown, return aggregate result."""
        result = ExecutorResult()
        all_steps = [
            ("setup", s) for s in self.testcase.setup
        ] + [
            ("steps", s) for s in self.testcase.steps
        ]
        for idx, (phase, step) in enumerate(all_steps):
            step_result = self._execute_step(step, idx)
            if not step_result.passed:
                result.passed = False
                result.message = step_result.message
                result.step_index = idx
                result.errors.extend(step_result.errors)
                break

        for tear in self.testcase.teardown:
            try:
                handler = ACTION_HANDLERS.get(tear.action)
                if handler:
                    handler(tear, self.context)
            except Exception:
                pass
        return result

    def _execute_step(
        self, step: ActionStep, idx: int
    ) -> ExecutorResult:
        """Execute a single step: wait_for → action → asserts → wait_after."""
        result = ExecutorResult(step_index=idx)
        step_label = step.name or step.action

        if step.wait_for:
            from src.yaml_test.wait import wait_for

            sel_dict = step.wait_for.selector.model_dump(exclude_none=True)
            found = wait_for(
                sel_dict,
                timeout=step.wait_for.timeout,
                interval=step.wait_for.interval,
            )
            if not found:
                result.passed = False
                result.message = (
                    f"Step [{step_label}]: wait_for timed out "
                    f"({step.wait_for.timeout}ms)"
                )
                return result

        handler = ACTION_HANDLERS.get(step.action)
        if handler is None:
            result.passed = False
            result.message = f"Step [{step_label}]: unknown action '{step.action}'"
            return result

        try:
            handler(step, self.context)
        except Exception as exc:
            result.passed = False
            result.message = f"Step [{step_label}] action '{step.action}' failed: {exc}"
            return result

        for assert_step in step.assert_steps:
            try:
                from src.yaml_test.assertions import run_assert

                run_assert(assert_step)
            except AssertionError as exc:
                result.passed = False
                result.message = (
                    f"Step [{step_label}] assert '{assert_step.type}' failed: {exc}"
                )
                return result
            except ValueError as exc:
                result.passed = False
                result.message = str(exc)
                return result

        if step.wait_after:
            time.sleep(step.wait_after / 1000.0)

        return result
