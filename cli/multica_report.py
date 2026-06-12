# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Multica integration: progress comments, Allure merge, and batch orchestration."""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from cli.run import _find_autotest_dir
from src.yaml_test.batch_runner import _merge_allure_dirs, install_sigterm_handler, run_batches


def _check_multica_cli() -> bool:
    if not shutil.which("multica"):
        print(
            "Warning: multica CLI not found. Tests will run but no progress "
            "comments will be posted.",
            flush=True,
        )
        return False
    config = Path.home() / ".multica" / "config.json"
    if not config.exists():
        print(
            "Warning: multica auth config not found. Tests will run but no progress "
            "comments will be posted.",
            flush=True,
        )
        return False
    return True


def _post_multica_comment(issue_id: str, content: str) -> None:
    try:
        subprocess.run(
            ["multica", "issue", "comment", "add", issue_id, "--content", content],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Warning: Failed to post multica comment: {e}", file=sys.stderr, flush=True)


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"


def _format_start_comment(
    app: str,
    module: str,
    tag: str,
    total: int,
    batches: int,
    batch_size: int,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "🚀 **YouQu Test Started**",
        f"- App: `{app}`",
    ]
    if module:
        lines.append(f"- Module: `{module}`")
    if tag:
        lines.append(f"- Tags: `{tag}`")
    lines.extend([
        f"- Cases: {total} | Batches: {batches} (batch size: {batch_size})",
        f"- Started: {now}",
    ])
    return "\n".join(lines)


def _format_batch_comment(
    batch_num: int,
    total_batches: int,
    case_range: str,
    passed: int,
    failed: int,
    timeout: int,
    skipped: int,
    duration: float,
) -> str:
    total = passed + failed + timeout + skipped
    rate = f"{passed / total * 100:.1f}%" if total > 0 else "N/A"
    lines = [
        f"📊 **Progress: Batch {batch_num}/{total_batches}**",
        f"- Batch: {case_range}",
        f"- Passed: {passed} | Failed: {failed} | Timeout: {timeout} | Skipped: {skipped}",
        f"- Pass Rate: {rate}",
        f"- Time: {_format_duration(duration)}",
    ]
    return "\n".join(lines)


def _format_finish_comment(
    total: int,
    passed: int,
    failed: int,
    timeout: int,
    skipped: int,
    duration: float,
    allure_path: str,
) -> str:
    effective = passed + failed + timeout + skipped
    rate = f"{passed / effective * 100:.1f}%" if effective > 0 else "N/A"
    partial = " (partial)" if (failed + timeout) > 0 else ""
    icon = "✅" if (failed + timeout) == 0 else "⚠️"
    lines = [
        f"{icon} **YouQu Test Complete{partial}**",
        f"- Total: {total} | Passed: {passed} | Failed: {failed} "
        f"| Timeout: {timeout} | Skipped: {skipped}",
        f"- Pass Rate: {rate}",
        f"- Duration: {_format_duration(duration)}",
        f"- Allure: `{allure_path}` (local path)",
    ]
    return "\n".join(lines)


def _format_cancel_comment(completed_batches: int, total_batches: int) -> str:
    return f"⏹️ Cancelled by user. Completed {completed_batches}/{total_batches} batches."


def run_multica(
    autotest_path: str | None,
    issue_id: str,
    batch_size: int,
    case_timeout: int,
    module: str,
    tag: str,
) -> int:
    """Orchestrate batch test execution with multica progress comments.

    Returns 0 if all tests passed, 1 otherwise.
    """
    from src.yaml_test.index import YamlIndex

    start_time = time.time()
    multica_available = _check_multica_cli()

    autotest = _find_autotest_dir(autotest_path)
    yaml_dir = autotest / "yaml"

    if not yaml_dir.exists():
        print(f"Error: YAML directory not found: {yaml_dir}")
        return 1

    tag_list = tag.split(",") if tag else None

    index = YamlIndex(yaml_dir)
    tests = index.query(module=module or None, tags=tag_list)

    if not tests:
        msg = "No test cases found matching the given filters."
        print(msg, flush=True)
        if multica_available:
            _post_multica_comment(issue_id, msg)
        return 0

    test_ids = [t["id"] for t in tests]
    file_map = {t["id"]: t["file"] for t in tests}

    total_batches = (len(test_ids) + batch_size - 1) // batch_size
    app_name = autotest.name

    if multica_available:
        start_comment = _format_start_comment(
            app=app_name,
            module=module,
            tag=tag,
            total=len(test_ids),
            batches=total_batches,
            batch_size=batch_size,
        )
        _post_multica_comment(issue_id, start_comment)

    install_sigterm_handler()

    _prev_time = [start_time]

    def _on_batch_complete(batch_result: dict) -> None:
        if not multica_available:
            return
        now = time.time()
        batch_duration = now - _prev_time[0]
        _prev_time[0] = now
        batch_num = batch_result["batch"]
        cases = batch_result["cases"]
        case_range = f"{cases[0]}..{cases[-1]}"
        comment = _format_batch_comment(
            batch_num=batch_num,
            total_batches=total_batches,
            case_range=case_range,
            passed=batch_result["passed"],
            failed=batch_result["failed"],
            timeout=batch_result["timeout"],
            skipped=batch_result["skipped"],
            duration=batch_duration,
        )
        _post_multica_comment(issue_id, comment)

    result = run_batches(
        test_ids=test_ids,
        yaml_dir=str(yaml_dir),
        pytest_ini_dir=str(autotest),
        batch_size=batch_size,
        case_timeout=case_timeout,
        per_batch_callback=_on_batch_complete,
        cancel_event=None,
        file_map=file_map,
    )

    duration = time.time() - start_time

    report_root = autotest / "report"
    _merge_allure_dirs(report_root)
    allure_path = str(report_root / "allure_raw")

    if multica_available:
        if result["status"] == "cancelled":
            comment = _format_cancel_comment(
                completed_batches=result["completed_batches"],
                total_batches=result["total_batches"],
            )
        else:
            comment = _format_finish_comment(
                total=result["total"],
                passed=result["passed"],
                failed=result["failed"],
                timeout=result["timeout"],
                skipped=result["skipped"],
                duration=duration,
                allure_path=allure_path,
            )
        _post_multica_comment(issue_id, comment)

    if result["status"] == "cancelled":
        return 1
    return 0 if (result["failed"] + result["timeout"]) == 0 else 1
