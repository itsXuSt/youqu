# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for src.yaml_test.wait."""

from unittest.mock import MagicMock, patch

from src.yaml_test.wait import wait_for


class TestWaitForFoundImmediately:
    @patch("src.dogtail_utils.DogtailUtils")
    def test_wait_for_found_immediately(self, mock_dog_cls):
        mock_dog = MagicMock()
        mock_dog.find_elements_by_attr.return_value = [MagicMock()]
        mock_dog_cls.return_value = mock_dog

        result = wait_for({"name": "OK"}, timeout=5000, interval=100)
        assert result is True
        mock_dog.find_elements_by_attr.assert_called_once_with("$//OK/")


class TestWaitForFoundAfterPoll:
    @patch("src.dogtail_utils.DogtailUtils")
    def test_wait_for_found_after_poll(self, mock_dog_cls):
        mock_dog = MagicMock()
        mock_dog.find_elements_by_attr.side_effect = [
            [],
            [],
            [MagicMock()],
        ]
        mock_dog_cls.return_value = mock_dog

        result = wait_for({"name": "dialog"}, timeout=5000, interval=10)
        assert result is True
        assert mock_dog.find_elements_by_attr.call_count == 3


class TestWaitForTimeout:
    @patch("src.dogtail_utils.DogtailUtils")
    @patch("src.yaml_test.wait.time.sleep")
    @patch("src.yaml_test.wait.time.time")
    def test_wait_for_timeout(self, mock_time, mock_sleep, mock_dog_cls):
        mock_time.side_effect = [0.0, 0.001, 0.051]
        mock_dog = MagicMock()
        mock_dog.find_elements_by_attr.return_value = []
        mock_dog_cls.return_value = mock_dog

        result = wait_for({"name": "missing"}, timeout=50, interval=10)
        assert result is False


class TestWaitForEmptySelector:
    @patch("src.dogtail_utils.DogtailUtils")
    def test_wait_for_empty_selector(self, mock_dog_cls):
        result = wait_for({}, timeout=5000, interval=100)
        assert result is False
        mock_dog_cls.assert_not_called()

    @patch("src.dogtail_utils.DogtailUtils")
    def test_wait_for_none_selector(self, mock_dog_cls):
        result = wait_for(None, timeout=5000, interval=100)
        assert result is False
        mock_dog_cls.assert_not_called()
