# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for src.yaml_test.batch_runner."""

import signal
import subprocess
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.yaml_test.batch_runner import (
    _merge_allure_dirs,
    _on_sigterm,
    _parse_pytest_output,
    install_sigterm_handler,
    run_batches,
)

_POPEN_RET = MagicMock(returncode=0, stdout=b"1 passed, 0 failed, 0 skipped", stderr=b"")


def _make_popen_mock(stdout="1 passed, 0 failed, 0 skipped", returncode=0):
    proc = MagicMock(returncode=returncode, stdout=stdout, stderr="")
    proc.communicate.return_value = (stdout, "")
    return proc


def _setup_yaml_dir(tmp_path, test_ids):
    yaml_dir = tmp_path / "yaml"
    yaml_dir.mkdir()
    for tid in test_ids:
        (yaml_dir / f"{tid}.yaml").write_text("")
    return yaml_dir


class TestParsePytestOutput:
    def test_standard_output(self):
        result = _parse_pytest_output("1 passed, 0 failed, 0 skipped")
        assert result == {"passed": 1, "failed": 0, "skipped": 0}

    def test_with_failures(self):
        result = _parse_pytest_output("5 passed, 2 failed, 1 skipped")
        assert result["passed"] == 5
        assert result["failed"] == 2
        assert result["skipped"] == 1

    def test_empty_output(self):
        result = _parse_pytest_output("")
        assert result == {"passed": 0, "failed": 0, "skipped": 0}

    def test_multiline_output(self):
        output = "\n".join([
            "some header",
            "test_play_001 PASSED",
            "5 passed, 1 failed, 0 skipped",
            "some footer",
        ])
        result = _parse_pytest_output(output)
        assert result["passed"] == 5
        assert result["failed"] == 1

    def test_no_match(self):
        result = _parse_pytest_output("some other output without counts")
        assert result == {"passed": 0, "failed": 0, "skipped": 0}


class TestRunBatchesNormal:
    @patch("src.yaml_test.batch_runner.subprocess.Popen")
    def test_normal_execution(self, mock_popen, tmp_path):
        mock_popen.return_value = _make_popen_mock("1 passed, 0 failed, 0 skipped")
        yaml_dir = _setup_yaml_dir(tmp_path, ["test_001", "test_002", "test_003"])
        pytest_ini = tmp_path

        result = run_batches(
            test_ids=["test_001", "test_002", "test_003"],
            yaml_dir=str(yaml_dir),
            pytest_ini_dir=str(pytest_ini),
            batch_size=2,
        )

        assert result["total"] == 3
        assert result["passed"] == 3
        assert result["failed"] == 0
        assert result["status"] == "completed"
        assert result["completed_batches"] == 2
        assert len(result["batches"]) == 2
        assert mock_popen.call_count == 3

    @patch("src.yaml_test.batch_runner.subprocess.Popen")
    def test_single_batch(self, mock_popen, tmp_path):
        mock_popen.return_value = _make_popen_mock("2 passed, 0 failed, 0 skipped")
        yaml_dir = _setup_yaml_dir(tmp_path, ["test_001", "test_002"])

        result = run_batches(
            test_ids=["test_001", "test_002"],
            yaml_dir=str(yaml_dir),
            pytest_ini_dir=str(tmp_path),
            batch_size=10,
        )

        assert result["completed_batches"] == 1
        assert len(result["batches"]) == 1
        assert result["batches"][0]["cases"] == ["test_001", "test_002"]

    @patch("src.yaml_test.batch_runner.subprocess.Popen")
    def test_file_map(self, mock_popen, tmp_path):
        mock_popen.return_value = _make_popen_mock("1 passed, 0 failed, 0 skipped")
        yaml_dir = tmp_path / "yaml"
        yaml_dir.mkdir()
        (yaml_dir / "custom_name.yaml").write_text("")

        result = run_batches(
            test_ids=["test_001"],
            yaml_dir=str(yaml_dir),
            pytest_ini_dir=str(tmp_path),
            batch_size=10,
            file_map={"test_001": "custom_name.yaml"},
        )

        assert result["passed"] == 1
        cmd = mock_popen.call_args[0][0]
        assert any("custom_name.yaml" in str(c) for c in cmd)

    @patch("src.yaml_test.batch_runner.subprocess.Popen")
    def test_per_case_callback(self, mock_popen, tmp_path):
        mock_popen.return_value = _make_popen_mock("1 passed, 0 failed, 0 skipped")
        yaml_dir = _setup_yaml_dir(tmp_path, ["test_001"])
        callback_results = []

        result = run_batches(
            test_ids=["test_001"],
            yaml_dir=str(yaml_dir),
            pytest_ini_dir=str(tmp_path),
            batch_size=10,
            per_case_callback=lambda r: callback_results.append(r),
        )

        assert len(callback_results) == 1
        assert callback_results[0]["test_id"] == "test_001"
        assert callback_results[0]["passed"] == 1


class TestRunBatchesTimeout:
    @patch("src.yaml_test.batch_runner.subprocess.Popen")
    def test_timeout_handling(self, mock_popen, tmp_path):
        proc_ok = _make_popen_mock("1 passed, 0 failed, 0 skipped")
        proc_timeout = _make_popen_mock()
        proc_timeout.communicate.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=90)
        proc_ok2 = _make_popen_mock("1 passed, 0 failed, 0 skipped")
        mock_popen.side_effect = [proc_ok, proc_timeout, proc_ok2]
        yaml_dir = _setup_yaml_dir(tmp_path, ["t1", "t2", "t3"])

        result = run_batches(
            test_ids=["t1", "t2", "t3"],
            yaml_dir=str(yaml_dir),
            pytest_ini_dir=str(tmp_path),
            batch_size=3,
        )

        assert result["passed"] == 2
        assert result["timeout"] == 1
        assert result["failed"] == 0
        assert result["status"] == "completed"


class TestRunBatchesEmpty:
    @patch("src.yaml_test.batch_runner.subprocess.Popen")
    def test_empty_test_ids(self, mock_popen):
        result = run_batches(test_ids=[], yaml_dir="/fake", pytest_ini_dir="/fake")
        assert result["total"] == 0
        assert result["status"] == "completed"
        assert result["completed_batches"] == 0
        assert result["total_batches"] == 0
        assert result["batches"] == []
        mock_popen.assert_not_called()


class TestRunBatchesCancel:
    @patch("src.yaml_test.batch_runner.subprocess.Popen")
    def test_cancel_between_batches(self, mock_popen, tmp_path):
        cancel_event = threading.Event()
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                cancel_event.set()
            return _make_popen_mock("1 passed, 0 failed, 0 skipped")

        mock_popen.side_effect = side_effect
        yaml_dir = _setup_yaml_dir(tmp_path, ["t1", "t2", "t3", "t4"])

        result = run_batches(
            test_ids=["t1", "t2", "t3", "t4"],
            yaml_dir=str(yaml_dir),
            pytest_ini_dir=str(tmp_path),
            batch_size=2,
            cancel_event=cancel_event,
        )

        assert result["status"] == "cancelled"
        assert result["completed_batches"] == 1

    @patch("src.yaml_test.batch_runner.subprocess.Popen")
    def test_cancel_before_any_batch(self, mock_popen, tmp_path):
        cancel_event = threading.Event()
        cancel_event.set()
        yaml_dir = _setup_yaml_dir(tmp_path, ["t1", "t2"])

        result = run_batches(
            test_ids=["t1", "t2"],
            yaml_dir=str(yaml_dir),
            pytest_ini_dir=str(tmp_path),
            batch_size=2,
            cancel_event=cancel_event,
        )

        assert result["status"] == "cancelled"
        assert result["completed_batches"] == 0
        mock_popen.assert_not_called()

    @patch("src.yaml_test.batch_runner.subprocess.Popen")
    def test_sigterm_cancellation(self, mock_popen, tmp_path):
        import src.yaml_test.batch_runner as mod
        mock_popen.return_value = _make_popen_mock("1 passed, 0 failed, 0 skipped")
        yaml_dir = _setup_yaml_dir(tmp_path, ["t1", "t2", "t3", "t4"])

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                mod._cancelled = True
            return _make_popen_mock("1 passed, 0 failed, 0 skipped")

        mock_popen.side_effect = side_effect

        result = run_batches(
            test_ids=["t1", "t2", "t3", "t4"],
            yaml_dir=str(yaml_dir),
            pytest_ini_dir=str(tmp_path),
            batch_size=2,
        )

        assert result["status"] == "cancelled"
        assert result["completed_batches"] == 1
        assert mod._cancelled is True
        mod.run_batches(
            test_ids=[], yaml_dir=str(yaml_dir), pytest_ini_dir=str(tmp_path),
        )
        assert mod._cancelled is False


class TestRunBatchesHeartbeat:
    @patch("src.yaml_test.batch_runner.subprocess.Popen")
    def test_heartbeat_every_10_cases(self, mock_popen, tmp_path, capsys):
        mock_popen.return_value = _make_popen_mock("1 passed, 0 failed, 0 skipped")
        test_ids = [f"t{i:03d}" for i in range(1, 26)]
        yaml_dir = _setup_yaml_dir(tmp_path, test_ids)

        result = run_batches(
            test_ids=test_ids,
            yaml_dir=str(yaml_dir),
            pytest_ini_dir=str(tmp_path),
            batch_size=25,
        )

        captured = capsys.readouterr()
        assert "[youqu] case 10/25 done" in captured.out
        assert "[youqu] case 20/25 done" in captured.out
        assert "[youqu] case 25/25 done" not in captured.out


class TestMergeAllureDirs:
    def test_merge_multiple_dirs(self, tmp_path):
        batch1 = tmp_path / "batch_1" / "case_001"
        batch1.mkdir(parents=True)
        (batch1 / "result.json").write_text('{"a": 1}')
        (batch1 / "environment.xml").write_text("<env/>")

        batch2 = tmp_path / "batch_2" / "case_002"
        batch2.mkdir(parents=True)
        (batch2 / "result.json").write_text('{"b": 2}')

        target = _merge_allure_dirs(tmp_path)

        assert target.exists()
        assert (target / "result.json").exists()
        assert (target / "environment.xml").read_text() == "<env/>"
        # First write wins: whichever batch_*/case_*/result.json is found first
        assert (target / "result.json").read_text() in ('{"a": 1}', '{"b": 2}')

    def test_merge_no_dirs(self, tmp_path):
        target = _merge_allure_dirs(tmp_path)
        assert target.exists()
        assert list(target.iterdir()) == []

    def test_merge_skips_non_dirs(self, tmp_path):
        (tmp_path / "batch_1").write_text("not a dir")
        target = _merge_allure_dirs(tmp_path)
        assert target.exists()
        assert list(target.iterdir()) == []


class TestInstallSigtermHandler:
    def test_install_handler(self):
        install_sigterm_handler()
        current = signal.getsignal(signal.SIGTERM)
        assert current == _on_sigterm

    def test_handler_sets_cancelled(self):
        import src.yaml_test.batch_runner as mod
        mod._cancelled = False
        _on_sigterm(signal.SIGTERM, None)
        assert mod._cancelled is True
        mod._cancelled = False


class TestRunBatchesSkipped:
    @patch("src.yaml_test.batch_runner.subprocess.Popen")
    def test_all_skipped(self, mock_popen, tmp_path):
        mock_popen.return_value = _make_popen_mock("0 passed, 1 skipped")
        yaml_dir = _setup_yaml_dir(tmp_path, ["t1"])

        result = run_batches(
            test_ids=["t1"],
            yaml_dir=str(yaml_dir),
            pytest_ini_dir=str(tmp_path),
        )

        assert result["passed"] == 0
        assert result["skipped"] == 1
        assert result["failed"] == 0

    @patch("src.yaml_test.batch_runner.subprocess.Popen")
    def test_nonzero_returncode(self, mock_popen, tmp_path):
        mock_popen.return_value = _make_popen_mock("0 passed, 0 failed", returncode=1)
        yaml_dir = _setup_yaml_dir(tmp_path, ["t1"])

        result = run_batches(
            test_ids=["t1"],
            yaml_dir=str(yaml_dir),
            pytest_ini_dir=str(tmp_path),
        )

        assert result["failed"] == 1
        assert result["passed"] == 0

    @patch("src.yaml_test.batch_runner.subprocess.Popen")
    def test_nonzero_returncode_with_passed_tests(self, mock_popen, tmp_path):
        mock_popen.return_value = _make_popen_mock(
            "5 passed, 0 failed, 1 skipped", returncode=1,
        )
        yaml_dir = _setup_yaml_dir(tmp_path, ["t1"])

        result = run_batches(
            test_ids=["t1"],
            yaml_dir=str(yaml_dir),
            pytest_ini_dir=str(tmp_path),
        )

        assert result["passed"] == 5
        assert result["failed"] == 0

    @patch("src.yaml_test.batch_runner.subprocess.Popen")
    def test_nonzero_returncode_with_failed_tests(self, mock_popen, tmp_path):
        mock_popen.return_value = _make_popen_mock(
            "3 passed, 2 failed, 0 skipped", returncode=1,
        )
        yaml_dir = _setup_yaml_dir(tmp_path, ["t1"])

        result = run_batches(
            test_ids=["t1"],
            yaml_dir=str(yaml_dir),
            pytest_ini_dir=str(tmp_path),
        )

        assert result["passed"] == 3
        assert result["failed"] == 2

    @patch("src.yaml_test.batch_runner.subprocess.Popen")
    def test_zero_exit_zero_parsed_fallback_skipped(self, mock_popen, tmp_path):
        mock_popen.return_value = _make_popen_mock("no useful output")
        yaml_dir = _setup_yaml_dir(tmp_path, ["t1"])

        result = run_batches(
            test_ids=["t1"],
            yaml_dir=str(yaml_dir),
            pytest_ini_dir=str(tmp_path),
        )

        assert result["skipped"] == 1
        assert result["failed"] == 0
        assert result["passed"] == 0
