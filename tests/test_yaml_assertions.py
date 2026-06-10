# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for src.yaml_test.assertions."""

from unittest.mock import MagicMock, patch

import pytest

from src.yaml_test.assertions import ASSERT_HANDLERS, run_assert
from src.yaml_test.parser import AssertStep, Selector

_MOCK_AC = "src.assert_common.AssertCommon"


def _ac_patch(attr):
    return patch(f"{_MOCK_AC}.{attr}", create=True)


class TestElementVisible:
    @_ac_patch("assert_element_exist")
    def test_assert_element_visible_pass(self, mock_assert):
        mock_assert.return_value = None
        step = AssertStep(
            type="element_visible",
            selector=Selector(name="OK"),
        )
        run_assert(step)
        mock_assert.assert_called_once_with("$//OK/")

    @_ac_patch("assert_element_exist")
    def test_assert_element_visible_fail(self, mock_assert):
        mock_assert.side_effect = AssertionError("element not found")
        step = AssertStep(
            type="element_visible",
            selector=Selector(name="Missing"),
        )
        with pytest.raises(AssertionError, match="element not found"):
            run_assert(step)


class TestElementNotVisible:
    @_ac_patch("assert_element_not_exist")
    def test_assert_element_not_visible(self, mock_assert):
        mock_assert.return_value = None
        step = AssertStep(
            type="element_not_visible",
            selector=Selector(name="hidden"),
        )
        run_assert(step)
        mock_assert.assert_called_once_with("$//hidden/")


class TestElementNumbers:
    @_ac_patch("assert_element_numbers")
    def test_assert_element_numbers(self, mock_assert):
        mock_assert.return_value = None
        step = AssertStep(
            type="element_numbers",
            selector=Selector(name="tab"),
            number=5,
        )
        run_assert(step)
        mock_assert.assert_called_once_with("$//tab/", 5)


class TestFileExists:
    @_ac_patch("assert_file_exist")
    def test_assert_file_exists(self, mock_assert):
        mock_assert.return_value = True
        step = AssertStep(type="file_exists", path="/tmp/test.txt")
        run_assert(step)
        mock_assert.assert_called_once_with("/tmp/test.txt")

    @_ac_patch("assert_file_not_exist")
    def test_assert_file_not_exists(self, mock_assert):
        step = AssertStep(type="file_not_exists", path="/tmp/missing.txt")
        run_assert(step)
        mock_assert.assert_called_once_with("/tmp/missing.txt")


class TestProcessRunning:
    @_ac_patch("assert_process_status")
    def test_assert_process_running(self, mock_assert):
        step = AssertStep(type="process_running", app="deepin-reader")
        run_assert(step)
        mock_assert.assert_called_once_with(True, "deepin-reader")

    @_ac_patch("assert_process_status")
    def test_assert_process_not_running(self, mock_assert):
        step = AssertStep(type="process_not_running", app="deepin-reader")
        run_assert(step)
        mock_assert.assert_called_once_with(False, "deepin-reader")


class TestImageExist:
    @_ac_patch("assert_image_exist")
    def test_assert_image_exist(self, mock_assert):
        step = AssertStep(type="image_exist", path="/tmp/btn.png")
        run_assert(step)
        mock_assert.assert_called_once_with("/tmp/btn.png")

    @_ac_patch("assert_image_not_exist")
    def test_assert_image_not_exist(self, mock_assert):
        step = AssertStep(type="image_not_exist", path="/tmp/btn.png")
        run_assert(step)
        mock_assert.assert_called_once_with("/tmp/btn.png")


class TestOcrExist:
    @_ac_patch("assert_ocr_exist")
    def test_assert_ocr_exist(self, mock_assert):
        step = AssertStep(type="ocr_exist", value="确定")
        run_assert(step)
        mock_assert.assert_called_once_with("确定")

    @_ac_patch("assert_ocr_not_exist")
    def test_assert_ocr_not_exist(self, mock_assert):
        step = AssertStep(type="ocr_not_exist", value="取消")
        run_assert(step)
        mock_assert.assert_called_once_with("取消")


class TestUnknownAssert:
    def test_unknown_assert_type_raises(self):
        step = AssertStep(type="nonexistent_assert")
        with pytest.raises(ValueError, match="Unknown assert type"):
            run_assert(step)

    def test_all_15_handlers_present(self):
        expected_types = {
            "element_visible", "element_not_visible", "element_numbers",
            "element_text", "process_running", "process_not_running",
            "file_exists", "file_not_exists", "image_exist", "image_not_exist",
            "ocr_exist", "ocr_not_exist", "window_size", "window_amount",
            "dbus_property",
        }
        assert set(ASSERT_HANDLERS.keys()) == expected_types
