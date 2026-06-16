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
    _parse_junit_xml,
    install_sigterm_handler,
    run_batches,
)

_NO_ERROR: list[str] = []


def _make_junit_xml(
    passed: int = 0,
    failed: int = 0,
    skipped: int = 0,
    errors: list[str] | None = None,
) -> str:
    if errors is None:
        errors = [f"Error {i}" for i in range(failed)]
    cases: list[str] = []
    for i in range(passed):
        cases.append(f'<testcase name="pass_{i}" time="0.0" />')
    for i in range(failed):
        msg = errors[i] if i < len(errors) else f"Error {i}"
        escaped = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        cases.append(
            f'<testcase name="fail_{i}" time="0.0">'
            f'<failure message="{escaped}">traceback</failure>'
            f"</testcase>"
        )
    for i in range(skipped):
        cases.append(f'<testcase name="skip_{i}" time="0.0"><skipped /></testcase>')
    inner = "".join(cases)
    return f'<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite>{inner}</testsuite></testsuites>'


def _popen_fn(
    passed: int = 1,
    failed: int = 0,
    skipped: int = 0,
    errors: list[str] | None = None,
    returncode: int | None = None,
):
    if returncode is None:
        returncode = 1 if failed > 0 else 0
    xml = _make_junit_xml(passed, failed, skipped, errors)

    def side_effect(cmd, *args, **kwargs):
        for c in cmd:
            if isinstance(c, str) and c.startswith("--junitxml="):
                p = Path(c.split("=", 1)[1])
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(xml, encoding="utf-8")
                break
        proc = MagicMock(returncode=returncode)
        proc.communicate.return_value = ("", "")
        return proc

    return side_effect


def _setup_yaml_dir(tmp_path, test_ids):
    yaml_dir = tmp_path / "yaml"
    yaml_dir.mkdir()
    for tid in test_ids:
        (yaml_dir / f"{tid}.yaml").write_text("")
    return yaml_dir


class TestParseJunitXml:
    def test_all_passed(self, tmp_path):
        xml = _make_junit_xml(passed=3)
        p = tmp_path / "junit.xml"
        p.write_text(xml, encoding="utf-8")
        result = _parse_junit_xml(p)
        assert result["passed"] == 3
        assert result["failed"] == 0
        assert result["skipped"] == 0
        assert result["errors"] == {}

    def test_with_failures(self, tmp_path):
        xml = _make_junit_xml(passed=2, failed=2, errors=["ElementNotFound", "Timeout"])
        p = tmp_path / "junit.xml"
        p.write_text(xml, encoding="utf-8")
        result = _parse_junit_xml(p)
        assert result["passed"] == 2
        assert result["failed"] == 2
        assert len(result["errors"]) == 2
        assert "ElementNotFound" in result["errors"]["fail_0"]
        assert "Timeout" in result["errors"]["fail_1"]

    def test_with_skipped(self, tmp_path):
        xml = _make_junit_xml(skipped=1)
        p = tmp_path / "junit.xml"
        p.write_text(xml, encoding="utf-8")
        result = _parse_junit_xml(p)
        assert result["skipped"] == 1
        assert result["passed"] == 0

    def test_chinese_error_message(self, tmp_path):
        xml = _make_junit_xml(failed=1, errors=['Step [1] failed: 未找到"$/xxx/"元素！'])
        p = tmp_path / "junit.xml"
        p.write_text(xml, encoding="utf-8")
        result = _parse_junit_xml(p)
        assert "未找到" in result["errors"]["fail_0"]

    def test_missing_file(self, tmp_path):
        result = _parse_junit_xml(tmp_path / "nonexistent.xml")
        assert result["passed"] == 0
        assert result["failed"] == 0
        assert result["errors"] == {}

    def test_malformed_xml(self, tmp_path):
        p = tmp_path / "bad.xml"
        p.write_text("not xml at all", encoding="utf-8")
        result = _parse_junit_xml(p)
        assert result["passed"] == 0
        assert result["errors"] == {}

    def test_error_message_truncated(self, tmp_path):
        long_msg = "x" * 600
        xml = _make_junit_xml(failed=1, errors=[long_msg])
        p = tmp_path / "junit.xml"
        p.write_text(xml, encoding="utf-8")
        result = _parse_junit_xml(p)
        assert len(result["errors"]["fail_0"]) <= 500


class TestRunBatchesNormal:
    @patch("src.yaml_test.batch_runner.subprocess.Popen")
    def test_normal_execution(self, mock_popen, tmp_path):
        mock_popen.side_effect = _popen_fn(passed=1)
        yaml_dir = _setup_yaml_dir(tmp_path, ["test_001", "test_002", "test_003"])

        result = run_batches(
            test_ids=["test_001", "test_002", "test_003"],
            yaml_dir=str(yaml_dir),
            pytest_ini_dir=str(tmp_path),
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
        mock_popen.side_effect = _popen_fn(passed=1)
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
        mock_popen.side_effect = _popen_fn(passed=1)
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
        mock_popen.side_effect = _popen_fn(passed=1)
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

    @patch("src.yaml_test.batch_runner.subprocess.Popen")
    def test_failure_error_extracted(self, mock_popen, tmp_path):
        mock_popen.side_effect = _popen_fn(
            failed=1, errors=["Step [1] action failed: ElementNotFound"],
        )
        yaml_dir = _setup_yaml_dir(tmp_path, ["t1"])

        result = run_batches(
            test_ids=["t1"],
            yaml_dir=str(yaml_dir),
            pytest_ini_dir=str(tmp_path),
        )

        assert result["failed"] == 1
        assert len(result["batches"][0]["failures"]) == 1
        assert "ElementNotFound" in result["batches"][0]["failures"][0]["error"]


class TestRunBatchesTimeout:
    @patch("src.yaml_test.batch_runner.subprocess.Popen")
    def test_timeout_handling(self, mock_popen, tmp_path):
        proc_ok = MagicMock(returncode=0)
        proc_ok.communicate.return_value = ("", "")
        proc_timeout = MagicMock()
        proc_timeout.communicate.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=90)

        call_count = [0]

        def side_effect(cmd, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                return proc_timeout
            for c in cmd:
                if isinstance(c, str) and c.startswith("--junitxml="):
                    p = Path(c.split("=", 1)[1])
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(_make_junit_xml(passed=1), encoding="utf-8")
                    break
            return MagicMock(returncode=0, communicate=MagicMock(return_value=("", "")))

        mock_popen.side_effect = side_effect
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

        def side_effect(cmd, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                cancel_event.set()
            for c in cmd:
                if isinstance(c, str) and c.startswith("--junitxml="):
                    p = Path(c.split("=", 1)[1])
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(_make_junit_xml(passed=1), encoding="utf-8")
                    break
            proc = MagicMock(returncode=0)
            proc.communicate.return_value = ("", "")
            return proc

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
        yaml_dir = _setup_yaml_dir(tmp_path, ["t1", "t2", "t3", "t4"])

        call_count = [0]

        def side_effect(cmd, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                mod._cancelled = True
            for c in cmd:
                if isinstance(c, str) and c.startswith("--junitxml="):
                    p = Path(c.split("=", 1)[1])
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(_make_junit_xml(passed=1), encoding="utf-8")
                    break
            proc = MagicMock(returncode=0)
            proc.communicate.return_value = ("", "")
            return proc

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
    def test_heartbeat_every_10_cases(self, mock_popen, tmp_path):
        mock_popen.side_effect = _popen_fn(passed=1)
        test_ids = [f"t{i:03d}" for i in range(1, 26)]
        yaml_dir = _setup_yaml_dir(tmp_path, test_ids)

        result = run_batches(
            test_ids=test_ids,
            yaml_dir=str(yaml_dir),
            pytest_ini_dir=str(tmp_path),
            batch_size=25,
        )

        captured = capsys = pytest.CaptureFixture


class TestMergeAllureDirs:
    def test_merge_multiple_dirs(self, tmp_path):
        batch1 = tmp_path / "batch_1" / "case_001"
        batch1.mkdir(parents=True)
        (batch1 / "result.json").write_text('{"a": 1}')

        batch2 = tmp_path / "batch_2" / "case_002"
        batch2.mkdir(parents=True)
        (batch2 / "result.json").write_text('{"b": 2}')

        target = _merge_allure_dirs(tmp_path)

        assert target.exists()
        assert (target / "result.json").exists()
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

    def test_merge_skips_non_json_files(self, tmp_path):
        batch1 = tmp_path / "batch_1" / "case_001"
        batch1.mkdir(parents=True)
        (batch1 / "result.json").write_text('{"a": 1}')
        (batch1 / "junit.xml").write_text("<?xml version='1.0'?><x/>")

        target = _merge_allure_dirs(tmp_path)

        assert (target / "result.json").exists()
        assert not (target / "junit.xml").exists()


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
        mock_popen.side_effect = _popen_fn(passed=0, skipped=1)
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
        mock_popen.side_effect = _popen_fn(passed=0, failed=0, returncode=1)
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
        mock_popen.side_effect = _popen_fn(passed=5, skipped=1, returncode=1)
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
        mock_popen.side_effect = _popen_fn(passed=3, failed=2, returncode=1)
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
        def side_effect(cmd, *args, **kwargs):
            proc = MagicMock(returncode=0)
            proc.communicate.return_value = ("", "")
            return proc

        mock_popen.side_effect = side_effect
        yaml_dir = _setup_yaml_dir(tmp_path, ["t1"])

        result = run_batches(
            test_ids=["t1"],
            yaml_dir=str(yaml_dir),
            pytest_ini_dir=str(tmp_path),
        )

        assert result["skipped"] == 1
        assert result["failed"] == 0
        assert result["passed"] == 0
