# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for cli.multica_report."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from cli.multica_report import (
    _check_multica_cli,
    _format_batch_comment,
    _format_cancel_comment,
    _format_duration,
    _format_finish_comment,
    _format_start_comment,
    _post_multica_comment,
    run_multica,
)


class TestCheckMulticaCli:
    """Tests for _check_multica_cli()."""

    @patch("cli.multica_report.Path")
    @patch("cli.multica_report.shutil.which")
    def test_cli_missing(self, mock_which, mock_path_cls):
        mock_which.return_value = None
        assert _check_multica_cli() is False

    @patch("cli.multica_report.shutil.which")
    def test_cli_found_auth_ok(self, mock_which):
        mock_which.return_value = "/usr/bin/multica"
        with patch("cli.multica_report.Path.home") as mock_home:
            mock_home.return_value.__truediv__ = lambda self, other: MagicMock(
                __truediv__=lambda self, other: MagicMock(exists=MagicMock(return_value=True)),
            )
            assert _check_multica_cli() is True

    @patch("cli.multica_report.shutil.which")
    def test_cli_found_no_auth(self, mock_which):
        mock_which.return_value = "/usr/bin/multica"
        with patch("cli.multica_report.Path.home") as mock_home:
            mock_home.return_value.__truediv__ = lambda self, other: MagicMock(
                __truediv__=lambda self, other: MagicMock(exists=MagicMock(return_value=False)),
            )
            assert _check_multica_cli() is False


class TestFormatDuration:
    """Tests for _format_duration()."""

    def test_seconds(self):
        assert _format_duration(45) == "45s"

    def test_minutes_and_seconds(self):
        assert _format_duration(192) == "3m 12s"

    def test_zero(self):
        assert _format_duration(0) == "0s"

    def test_exact_minute(self):
        assert _format_duration(60) == "1m 0s"

    def test_large_duration(self):
        assert _format_duration(3661) == "61m 1s"


class TestFormatStartComment:
    """Tests for _format_start_comment()."""

    def test_full_params(self):
        result = _format_start_comment("deepin-music", "播放", "L1", 205, 11, 20)
        assert "🚀 **YouQu Test Started**" in result
        assert "`deepin-music`" in result
        assert "`播放`" in result
        assert "205" in result
        assert "11 (batch size: 20)" in result
        assert "Started:" in result

    def test_no_module_no_tag(self):
        result = _format_start_comment("music", "", "", 10, 1, 10)
        assert "Module:" not in result
        assert "Tags:" not in result

    def test_module_only(self):
        result = _format_start_comment("app", "core", "", 5, 1, 5)
        assert "Module:" in result
        assert "Tags:" not in result

    def test_tag_only(self):
        result = _format_start_comment("app", "", "L1,smoke", 5, 1, 5)
        assert "Module:" not in result
        assert "Tags:" in result


class TestFormatBatchComment:
    """Tests for _format_batch_comment()."""

    def test_normal(self):
        result = _format_batch_comment(
            5, 11, "test_play_081..test_play_100", 17, 2, 1, 0, 192
        )
        assert "📊" in result
        assert "5/11" in result
        assert "85.0%" in result
        assert "3m 12s" in result

    def test_all_passed(self):
        result = _format_batch_comment(1, 1, "t1..t5", 5, 0, 0, 0, 10)
        assert "100.0%" in result

    def test_zero_total_shows_na(self):
        result = _format_batch_comment(1, 1, "none", 0, 0, 0, 0, 0)
        assert "N/A" in result

    def test_all_failed(self):
        result = _format_batch_comment(1, 1, "t1..t3", 0, 3, 0, 0, 10)
        assert "0.0%" in result


class TestFormatFinishComment:
    """Tests for _format_finish_comment()."""

    def test_all_passed(self):
        result = _format_finish_comment(
            205, 185, 17, 3, 2, 1695, "autotest/report/allure_html/"
        )
        assert "⚠️" in result
        assert "(partial)" in result
        assert "28m 15s" in result

    def test_all_passed_no_partial(self):
        result = _format_finish_comment(10, 10, 0, 0, 0, 60, "report/")
        assert "✅" in result
        assert "(partial)" not in result
        assert "100.0%" in result
        assert "1m 0s" in result

    def test_with_timeout(self):
        result = _format_finish_comment(5, 3, 0, 2, 0, 30, "report/")
        assert "⚠️" in result
        assert "(partial)" in result

    def test_zero_effective_shows_na(self):
        result = _format_finish_comment(0, 0, 0, 0, 0, 0, "report/")
        assert "N/A" in result
        assert "✅" in result


class TestFormatCancelComment:
    """Tests for _format_cancel_comment()."""

    def test_cancel_partial(self):
        result = _format_cancel_comment(5, 11)
        assert "⏹️" in result
        assert "5/11" in result

    def test_cancel_zero_batches(self):
        result = _format_cancel_comment(0, 5)
        assert "0/5" in result

    def test_cancel_all_done(self):
        result = _format_cancel_comment(3, 3)
        assert "3/3" in result


class TestPostMulticaComment:
    """Tests for _post_multica_comment()."""

    @patch("cli.multica_report.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        _post_multica_comment("MUL-1", "test content")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "multica" in cmd
        assert "MUL-1" in cmd

    @patch("cli.multica_report.subprocess.run")
    def test_failure_continues(self, mock_run, capsys):
        mock_run.side_effect = subprocess.CalledProcessError(1, "multica")
        _post_multica_comment("MUL-1", "test content")
        captured = capsys.readouterr()
        assert "Failed to post" in captured.err

    @patch("cli.multica_report.subprocess.run")
    def test_cli_not_found_continues(self, mock_run, capsys):
        mock_run.side_effect = FileNotFoundError("multica not found")
        _post_multica_comment("MUL-1", "test")
        captured = capsys.readouterr()
        assert "Failed to post" in captured.err


class TestRunMulticaOrchestrator:
    """Tests for run_multica() orchestration flow."""

    @patch("cli.multica_report._post_multica_comment")
    @patch("src.yaml_test.index.YamlIndex")
    @patch("cli.multica_report._find_autotest_dir")
    @patch("cli.multica_report._check_multica_cli")
    def test_zero_cases_exit_0(self, mock_check, mock_find, mock_index_cls, mock_post, tmp_path):
        mock_check.return_value = True
        mock_find.return_value = tmp_path
        (tmp_path / "yaml").mkdir()

        mock_index = MagicMock()
        mock_index.query.return_value = []
        mock_index_cls.return_value = mock_index

        result = run_multica(str(tmp_path), "MUL-1", 20, 90, "", "")
        assert result == 0
        mock_post.assert_called()

    @patch("cli.multica_report._post_multica_comment")
    @patch("src.yaml_test.index.YamlIndex")
    @patch("cli.multica_report._find_autotest_dir")
    @patch("cli.multica_report._check_multica_cli")
    def test_zero_cases_no_multica_no_post(
        self, mock_check, mock_find, mock_index_cls, mock_post, tmp_path
    ):
        mock_check.return_value = False
        mock_find.return_value = tmp_path
        (tmp_path / "yaml").mkdir()

        mock_index = MagicMock()
        mock_index.query.return_value = []
        mock_index_cls.return_value = mock_index

        run_multica(str(tmp_path), "MUL-1", 20, 90, "", "")
        mock_post.assert_not_called()

    @patch("cli.multica_report._merge_allure_dirs")
    @patch("cli.multica_report._post_multica_comment")
    @patch("cli.multica_report.install_sigterm_handler")
    @patch("cli.multica_report.run_batches")
    @patch("src.yaml_test.index.YamlIndex")
    @patch("cli.multica_report._find_autotest_dir")
    @patch("cli.multica_report._check_multica_cli")
    def test_all_pass_exit_0(
        self, mock_check, mock_find, mock_index_cls,
        mock_run_batches, mock_install, mock_post, mock_merge, tmp_path,
    ):
        mock_check.return_value = True
        mock_find.return_value = tmp_path
        (tmp_path / "yaml").mkdir()

        mock_index = MagicMock()
        mock_index.query.return_value = [
            {"id": "test_001", "file": "test_001.yaml"},
            {"id": "test_002", "file": "test_002.yaml"},
        ]
        mock_index_cls.return_value = mock_index

        mock_run_batches.return_value = {
            "status": "completed",
            "passed": 2,
            "failed": 0,
            "timeout": 0,
            "skipped": 0,
            "total": 2,
            "completed_batches": 1,
            "total_batches": 1,
            "batches": [
                {"batch": 1, "passed": 2, "failed": 0, "timeout": 0,
                 "skipped": 0, "cases": ["test_001", "test_002"]}
            ],
        }

        result = run_multica(str(tmp_path), "MUL-1", 20, 90, "", "")
        assert result == 0
        mock_run_batches.assert_called_once()
        mock_merge.assert_called_once()
        assert mock_post.call_count >= 2

    @patch("cli.multica_report._merge_allure_dirs")
    @patch("cli.multica_report._post_multica_comment")
    @patch("cli.multica_report.install_sigterm_handler")
    @patch("cli.multica_report.run_batches")
    @patch("src.yaml_test.index.YamlIndex")
    @patch("cli.multica_report._find_autotest_dir")
    @patch("cli.multica_report._check_multica_cli")
    def test_has_failures_exit_1(
        self, mock_check, mock_find, mock_index_cls,
        mock_run_batches, mock_install, mock_post, mock_merge, tmp_path,
    ):
        mock_check.return_value = True
        mock_find.return_value = tmp_path
        (tmp_path / "yaml").mkdir()

        mock_index = MagicMock()
        mock_index.query.return_value = [
            {"id": "test_001", "file": "test_001.yaml"},
        ]
        mock_index_cls.return_value = mock_index

        mock_run_batches.return_value = {
            "status": "completed",
            "passed": 0,
            "failed": 1,
            "timeout": 0,
            "skipped": 0,
            "total": 1,
            "completed_batches": 1,
            "total_batches": 1,
            "batches": [
                {"batch": 1, "passed": 0, "failed": 1, "timeout": 0,
                 "skipped": 0, "cases": ["test_001"]}
            ],
        }

        result = run_multica(str(tmp_path), "MUL-1", 20, 90, "", "")
        assert result == 1

    @patch("cli.multica_report._merge_allure_dirs")
    @patch("cli.multica_report._post_multica_comment")
    @patch("cli.multica_report.install_sigterm_handler")
    @patch("cli.multica_report.run_batches")
    @patch("src.yaml_test.index.YamlIndex")
    @patch("cli.multica_report._find_autotest_dir")
    @patch("cli.multica_report._check_multica_cli")
    def test_has_timeout_exit_1(
        self, mock_check, mock_find, mock_index_cls,
        mock_run_batches, mock_install, mock_post, mock_merge, tmp_path,
    ):
        mock_check.return_value = False
        mock_find.return_value = tmp_path
        (tmp_path / "yaml").mkdir()

        mock_index = MagicMock()
        mock_index.query.return_value = [
            {"id": "test_001", "file": "test_001.yaml"},
        ]
        mock_index_cls.return_value = mock_index

        mock_run_batches.return_value = {
            "status": "completed",
            "passed": 0,
            "failed": 0,
            "timeout": 1,
            "skipped": 0,
            "total": 1,
            "completed_batches": 1,
            "total_batches": 1,
            "batches": [
                {"batch": 1, "passed": 0, "failed": 0, "timeout": 1,
                 "skipped": 0, "cases": ["test_001"]}
            ],
        }

        result = run_multica(str(tmp_path), "MUL-1", 20, 90, "", "")
        assert result == 1
        mock_post.assert_not_called()

    @patch("cli.multica_report._post_multica_comment")
    @patch("src.yaml_test.index.YamlIndex")
    @patch("cli.multica_report._find_autotest_dir")
    @patch("cli.multica_report._check_multica_cli")
    def test_yaml_dir_missing_exit_1(
        self, mock_check, mock_find, mock_index_cls, mock_post, tmp_path
    ):
        mock_check.return_value = True
        mock_find.return_value = tmp_path

        result = run_multica(str(tmp_path), "MUL-1", 20, 90, "", "")
        assert result == 1
        mock_index_cls.assert_not_called()

    @patch("cli.multica_report._merge_allure_dirs")
    @patch("cli.multica_report._post_multica_comment")
    @patch("cli.multica_report.install_sigterm_handler")
    @patch("cli.multica_report.run_batches")
    @patch("src.yaml_test.index.YamlIndex")
    @patch("cli.multica_report._find_autotest_dir")
    @patch("cli.multica_report._check_multica_cli")
    def test_cancelled_status_posts_cancel_comment(
        self, mock_check, mock_find, mock_index_cls,
        mock_run_batches, mock_install, mock_post, mock_merge, tmp_path,
    ):
        mock_check.return_value = True
        mock_find.return_value = tmp_path
        (tmp_path / "yaml").mkdir()

        mock_index = MagicMock()
        mock_index.query.return_value = [
            {"id": "test_001", "file": "test_001.yaml"},
        ]
        mock_index_cls.return_value = mock_index

        mock_run_batches.return_value = {
            "status": "cancelled",
            "passed": 0,
            "failed": 0,
            "timeout": 0,
            "skipped": 0,
            "total": 1,
            "completed_batches": 0,
            "total_batches": 1,
            "batches": [],
        }

        result = run_multica(str(tmp_path), "MUL-1", 20, 90, "", "")
        assert result == 1
        last_call_content = mock_post.call_args[0][1]
        assert "Cancelled" in last_call_content

    @patch("cli.multica_report._merge_allure_dirs")
    @patch("cli.multica_report._post_multica_comment")
    @patch("cli.multica_report.install_sigterm_handler")
    @patch("cli.multica_report.run_batches")
    @patch("src.yaml_test.index.YamlIndex")
    @patch("cli.multica_report._find_autotest_dir")
    @patch("cli.multica_report._check_multica_cli")
    def test_multica_unavailable_still_runs(
        self, mock_check, mock_find, mock_index_cls,
        mock_run_batches, mock_install, mock_post, mock_merge, tmp_path,
    ):
        mock_check.return_value = False
        mock_find.return_value = tmp_path
        (tmp_path / "yaml").mkdir()

        mock_index = MagicMock()
        mock_index.query.return_value = [
            {"id": "test_001", "file": "test_001.yaml"},
        ]
        mock_index_cls.return_value = mock_index

        mock_run_batches.return_value = {
            "status": "completed",
            "passed": 1,
            "failed": 0,
            "timeout": 0,
            "skipped": 0,
            "total": 1,
            "completed_batches": 1,
            "total_batches": 1,
            "batches": [
                {"batch": 1, "passed": 1, "failed": 0, "timeout": 0,
                 "skipped": 0, "cases": ["test_001"]}
            ],
        }

        result = run_multica(str(tmp_path), "MUL-1", 20, 90, "", "")
        assert result == 0
        mock_post.assert_not_called()
        mock_merge.assert_called_once()
