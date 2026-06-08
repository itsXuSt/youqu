# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for src.yaml_test.executor."""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Pre-seed src.menu_nav in sys.modules so @patch("src.menu_nav.MenuNavigator")
# decorators work without triggering a real import.
if "src.menu_nav" not in sys.modules:
    sys.modules["src.menu_nav"] = MagicMock()

from src.yaml_test.executor import (
    ExecutorResult,
    StepExecutor,
    selector_to_expr,
)
from src.yaml_test.parser import ActionStep, AssertStep, Selector, TestCase


class TestSelectorToExpr:
    def test_selector_to_expr_name_only(self):
        assert selector_to_expr({"name": "OK"}) == "$/OK/"

    def test_selector_to_expr_empty_dict(self):
        assert selector_to_expr({}) == "$/"

    def test_selector_to_expr_none(self):
        assert selector_to_expr(None) == "$/"

    def test_selector_to_expr_with_role(self):
        result = selector_to_expr({"name": "打开", "role": "push button"})
        assert result == "$/打开/"

    def test_selector_to_expr_role_only(self):
        result = selector_to_expr({"role": "dialog"})
        assert result == "$/"

    def test_selector_to_expr_from_selector_model(self):
        sel = Selector(name="test_btn")
        assert selector_to_expr(sel) == "$/test_btn/"


def _make_testcase(steps, setup=None, teardown=None, app="test-app", elements=None):
    return TestCase(
        name="test",
        app=app,
        setup=setup or [],
        steps=steps,
        teardown=teardown or [],
        elements=elements or {},
    )


class TestKeyboardActions:
    @patch("src.yaml_test.executor._get_mk")
    def test_execute_keyboard_press(self, mock_get_mk):
        mk = MagicMock()
        mock_get_mk.return_value = mk
        tc = _make_testcase([ActionStep(action="keyboard_press", keys="Return")])
        result = StepExecutor(tc).run()
        assert result.passed
        mk.press_key.assert_called_once_with("Return")

    @patch("src.yaml_test.executor._get_mk")
    def test_execute_keyboard_hot_key_string(self, mock_get_mk):
        mk = MagicMock()
        mock_get_mk.return_value = mk
        tc = _make_testcase([ActionStep(action="keyboard_hot_key", keys="ctrl,s")])
        result = StepExecutor(tc).run()
        assert result.passed
        mk.hot_key.assert_called_once_with("ctrl", "s")

    @patch("src.yaml_test.executor._get_mk")
    def test_execute_keyboard_hot_key_list(self, mock_get_mk):
        mk = MagicMock()
        mock_get_mk.return_value = mk
        tc = _make_testcase([ActionStep(action="keyboard_hot_key", keys=["ctrl", "c"])])
        result = StepExecutor(tc).run()
        assert result.passed
        mk.hot_key.assert_called_once_with("ctrl", "c")

    @patch("src.yaml_test.executor._get_mk")
    def test_execute_keyboard_type(self, mock_get_mk):
        mk = MagicMock()
        mock_get_mk.return_value = mk
        tc = _make_testcase([ActionStep(action="keyboard_type", text="hello")])
        result = StepExecutor(tc).run()
        assert result.passed
        mk.input_message.assert_called_once_with("hello")


class TestMouseActions:
    @patch("src.yaml_test.executor._get_mk")
    def test_execute_mouse_click(self, mock_get_mk):
        mk = MagicMock()
        mock_get_mk.return_value = mk
        tc = _make_testcase([ActionStep(action="mouse_click", x=100, y=200)])
        result = StepExecutor(tc).run()
        assert result.passed
        mk.click.assert_called_once_with(100, 200)

    @patch("src.yaml_test.executor._get_mk")
    def test_execute_mouse_right_click(self, mock_get_mk):
        mk = MagicMock()
        mock_get_mk.return_value = mk
        tc = _make_testcase([ActionStep(action="mouse_right_click", x=50, y=60)])
        result = StepExecutor(tc).run()
        assert result.passed
        mk.right_click.assert_called_once_with(50, 60)

    @patch("src.yaml_test.executor._get_mk")
    def test_execute_mouse_scroll(self, mock_get_mk):
        mk = MagicMock()
        mock_get_mk.return_value = mk
        tc = _make_testcase([ActionStep(action="mouse_scroll", amount=-3)])
        result = StepExecutor(tc).run()
        assert result.passed
        mk.mouse_scroll.assert_called_once_with(-3)

    @patch("src.yaml_test.executor._get_mk")
    def test_execute_mouse_drag(self, mock_get_mk):
        mk = MagicMock()
        mock_get_mk.return_value = mk
        tc = _make_testcase([ActionStep(action="mouse_drag", x=300, y=400)])
        result = StepExecutor(tc).run()
        assert result.passed
        mk.drag_to.assert_called_once_with(300, 400)


class TestElementActions:
    @patch("src.yaml_test.executor._find_element")
    @patch("src.yaml_test.executor._get_dog")
    def test_execute_element_action_click(self, mock_get_dog, mock_find_element):
        element = MagicMock()
        mock_find_element.return_value = element
        dog = MagicMock()
        mock_get_dog.return_value = dog
        tc = _make_testcase([
            ActionStep(
                action="element_action",
                selector=Selector(name="OK"),
                do="click",
            )
        ])
        result = StepExecutor(tc).run()
        assert result.passed
        element.click.assert_called_once()

    @patch("src.yaml_test.executor._find_element")
    @patch("src.yaml_test.executor._get_dog")
    @patch("src.yaml_test.executor._get_mk")
    def test_execute_element_set_value(self, mock_get_mk, mock_get_dog, mock_find_element):
        element = MagicMock()
        mock_find_element.return_value = element
        dog = MagicMock()
        mock_get_dog.return_value = dog
        mk = MagicMock()
        mock_get_mk.return_value = mk

        tc = _make_testcase([
            ActionStep(
                action="element_set_value",
                selector=Selector(name="input_field"),
                text="hello world",
            )
        ])
        result = StepExecutor(tc).run()
        assert result.passed
        element.click.assert_called_once()
        mk.input_message.assert_called_once_with("hello world")


class TestSessionActions:
    @patch("src.yaml_test.executor.subprocess.Popen")
    def test_execute_session_start(self, mock_popen):
        mock_popen.return_value = MagicMock()
        tc = _make_testcase(
            [ActionStep(action="wait", wait=0.0)],
            setup=[ActionStep(action="session_start", command="deepin-reader", wait=0.0)],
        )
        result = StepExecutor(tc).run()
        assert result.passed
        mock_popen.assert_called_once_with(
            "deepin-reader", shell=True, start_new_session=True
        )

    @patch("src.yaml_test.executor.subprocess.run")
    def test_execute_session_stop(self, mock_run):
        tc = _make_testcase(
            [ActionStep(action="wait", wait=0.0)],
            teardown=[ActionStep(action="session_stop")],
            app="test-app",
        )
        result = StepExecutor(tc).run()
        assert result.passed
        mock_run.assert_called_once()


class TestMenuActions:
    @patch("src.menu_nav.MenuNavigator")
    def test_execute_main_menu_comb(self, mock_nav_cls):
        nav = MagicMock()
        mock_nav_cls.return_value = nav
        tc = _make_testcase([
            ActionStep(action="main_menu_comb", items=["文件", "打开"])
        ])
        result = StepExecutor(tc).run()
        assert result.passed
        nav.open_main_menu.assert_called_once()
        nav.select.assert_called_once_with(["文件", "打开"])

    @patch("src.menu_nav.MenuNavigator")
    def test_execute_context_menu_comb(self, mock_nav_cls):
        nav = MagicMock()
        mock_nav_cls.return_value = nav
        tc = _make_testcase([
            ActionStep(
                action="context_menu_comb",
                x=200,
                y=300,
                items=["复制"],
            )
        ])
        result = StepExecutor(tc).run()
        assert result.passed
        nav.open_context_menu.assert_called_once_with(200, 300)
        nav.select.assert_called_once_with(["复制"])


class TestWaitAndAssert:
    @patch("src.yaml_test.executor.time.sleep")
    def test_execute_wait_action(self, mock_sleep):
        tc = _make_testcase([ActionStep(action="wait", wait=0.5)])
        result = StepExecutor(tc).run()
        assert result.passed
        mock_sleep.assert_any_call(0.5)

    @patch("src.yaml_test.wait.time.sleep")
    @patch("src.yaml_test.wait.time.time")
    def test_execute_with_wait_for_success(self, mock_time, mock_sleep):
        mock_time.side_effect = [0, 0.001, 0.002]
        tc = _make_testcase([
            ActionStep(
                action="wait",
                wait=0.0,
                wait_for={
                    "selector": {"name": "dialog"},
                    "timeout": 5000,
                    "interval": 50,
                },
            )
        ])
        with patch("src.dogtail_utils.DogtailUtils") as mock_dog_cls:
            mock_dog = MagicMock()
            mock_dog.find_elements_by_attr.return_value = [MagicMock()]
            mock_dog_cls.return_value = mock_dog
            result = StepExecutor(tc).run()
            assert result.passed

    @patch("src.yaml_test.assertions.run_assert")
    def test_execute_with_assert_pass(self, mock_run_assert):
        tc = _make_testcase([
            ActionStep(
                action="wait",
                wait=0.0,
                assert_steps=[
                    AssertStep(type="element_visible", selector=Selector(name="OK")),
                ],
            )
        ])
        result = StepExecutor(tc).run()
        assert result.passed
        mock_run_assert.assert_called_once()

    @patch("src.yaml_test.assertions.run_assert")
    def test_execute_with_assert_fail(self, mock_run_assert):
        mock_run_assert.side_effect = AssertionError("not found")
        tc = _make_testcase([
            ActionStep(
                action="wait",
                wait=0.0,
                assert_steps=[
                    AssertStep(type="element_visible"),
                ],
            )
        ])
        result = StepExecutor(tc).run()
        assert not result.passed
        assert "assert" in result.message.lower()
        assert "not found" in result.message


class TestFailureHandling:
    def test_execute_unknown_action(self):
        tc = _make_testcase([ActionStep(action="nonexistent_action")])
        result = StepExecutor(tc).run()
        assert not result.passed
        assert "unknown action" in result.message

    @patch("src.yaml_test.executor._get_mk")
    def test_execute_step_exception_returns_failure(self, mock_get_mk):
        mock_get_mk.side_effect = RuntimeError("desktop not available")
        tc = _make_testcase([ActionStep(action="keyboard_press", keys="a")])
        result = StepExecutor(tc).run()
        assert not result.passed
        assert "failed" in result.message

    def test_teardown_runs_even_on_failure(self):
        teardown_called = []

        def mock_handler(step, ctx):
            teardown_called.append(step.action)

        tc = _make_testcase(
            [ActionStep(action="nonexistent")],
            teardown=[ActionStep(action="session_stop")],
        )
        with patch.dict(
            "src.yaml_test.executor.ACTION_HANDLERS",
            {"session_stop": mock_handler},
        ):
            result = StepExecutor(tc).run()
        assert not result.passed
        assert "session_stop" in teardown_called


_STANDARD_ELEMENTS = {
    "ok_button": {"name": "确定"},
    "main_frame": {"role": "frame"},
    "app_center": {"x": 500, "y": 300},
    "file_menu": {"name": "文件", "menu": ["文件", "打开"]},
    "context_pos": {"x": 100, "y": 200, "menu": ["复制", "粘贴"]},
}


class TestRefResolution:
    """Tests for ref-based element resolution (preferred path)."""

    @patch("src.yaml_test.executor._get_dog")
    def test_ref_element_action(self, mock_get_dog):
        element = MagicMock()
        dog = MagicMock()
        dog.find_element_by_attr.return_value = element
        mock_get_dog.return_value = dog
        tc = _make_testcase(
            [ActionStep(action="element_action", ref="ok_button", do="click")],
            elements=_STANDARD_ELEMENTS,
        )
        result = StepExecutor(tc).run()
        assert result.passed
        dog.find_element_by_attr.assert_called_once_with("$/确定/", 0)
        element.click.assert_called_once()

    @patch("src.yaml_test.executor._get_mk")
    def test_ref_mouse_click(self, mock_get_mk):
        mk = MagicMock()
        mock_get_mk.return_value = mk
        tc = _make_testcase(
            [ActionStep(action="mouse_click", ref="app_center")],
            elements=_STANDARD_ELEMENTS,
        )
        result = StepExecutor(tc).run()
        assert result.passed
        mk.click.assert_called_once_with(500, 300)

    @patch("src.yaml_test.executor._get_mk")
    def test_ref_mouse_right_click(self, mock_get_mk):
        mk = MagicMock()
        mock_get_mk.return_value = mk
        tc = _make_testcase(
            [ActionStep(action="mouse_right_click", ref="app_center")],
            elements=_STANDARD_ELEMENTS,
        )
        result = StepExecutor(tc).run()
        assert result.passed
        mk.right_click.assert_called_once_with(500, 300)

    @patch("src.yaml_test.executor._get_mk")
    def test_ref_mouse_drag(self, mock_get_mk):
        mk = MagicMock()
        mock_get_mk.return_value = mk
        tc = _make_testcase(
            [ActionStep(action="mouse_drag", ref="app_center")],
            elements=_STANDARD_ELEMENTS,
        )
        result = StepExecutor(tc).run()
        assert result.passed
        mk.drag_to.assert_called_once_with(500, 300)

    @patch("src.yaml_test.executor._get_dog")
    def test_ref_missing_raises(self, mock_get_dog):
        dog = MagicMock()
        mock_get_dog.return_value = dog
        tc = _make_testcase(
            [ActionStep(action="element_action", ref="nonexistent", do="click")],
            elements=_STANDARD_ELEMENTS,
        )
        result = StepExecutor(tc).run()
        assert not result.passed
        assert "nonexistent" in result.message
        dog.find_element_by_attr.assert_not_called()

    @patch("src.yaml_test.executor._get_dog")
    @patch("src.yaml_test.executor._get_mk")
    def test_ref_with_selectors(self, mock_get_mk, mock_get_dog):
        """When both ref and legacy selector are present, ref wins."""
        element = MagicMock()
        dog = MagicMock()
        dog.find_element_by_attr.return_value = element
        mock_get_dog.return_value = dog
        mk = MagicMock()
        mock_get_mk.return_value = mk
        tc = _make_testcase(
            [
                ActionStep(
                    action="element_action",
                    ref="ok_button",
                    selector=Selector(name="SHOULD_NOT_USE_THIS"),
                    do="click",
                )
            ],
            elements=_STANDARD_ELEMENTS,
        )
        result = StepExecutor(tc).run()
        assert result.passed
        dog.find_element_by_attr.assert_called_once_with("$/确定/", 0)

    @patch("src.yaml_test.executor._get_dog")
    @patch("src.yaml_test.executor._get_mk")
    def test_ref_with_xy(self, mock_get_mk, mock_get_dog):
        """When both ref and x/y are present, ref wins (no ambiguity)."""
        mk = MagicMock()
        mock_get_mk.return_value = mk
        tc = _make_testcase(
            [
                ActionStep(
                    action="mouse_click",
                    ref="app_center",
                    x=9999,
                    y=9999,
                )
            ],
            elements=_STANDARD_ELEMENTS,
        )
        result = StepExecutor(tc).run()
        assert result.passed
        mk.click.assert_called_once_with(500, 300)

    def test_ref_without_elements_fails_gracefully(self):
        tc = _make_testcase(
            [ActionStep(action="element_action", ref="ok_button", do="click")],
            elements={},  # no elements registered
        )
        result = StepExecutor(tc).run()
        assert not result.passed
        assert "ok_button" in result.message
