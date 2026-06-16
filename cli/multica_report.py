# SPDX-FileCopyrightText: 2026 Uniontech Software Technology Co., Ltd.
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
    skipped_count: int = 0,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    runnable = total - skipped_count
    lines = [
        "🚀 **YouQu Test Started**",
        f"- App: `{app}`",
    ]
    if module:
        lines.append(f"- Module: `{module}`")
    if tag:
        lines.append(f"- Tags: `{tag}`")
    lines.append(f"- Runnable: {runnable} | Skipped: {skipped_count} | Total: {total}")
    lines.append(f"- Batches: {batches} (batch size: {batch_size})")
    lines.append(f"- Started: {now}")
    return "\n".join(lines)


def _format_skip_comment(skipped_cases: list[dict]) -> str:
    lines = ["⏭️ **Skipped Cases**"]
    for case in skipped_cases:
        reason = case.get("skip") or "unknown"
        lines.append(f"- `{case['id']}`: {reason}")
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
    failures: list[dict] | None = None,
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
    if failures:
        lines.append("")
        lines.append("| Test ID | Error |")
        lines.append("|---------|-------|")
        for f in failures:
            error = f.get("error", "").replace("|", "\\|").replace("\n", " ")[:200]
            lines.append(f"| `{f['test_id']}` | {error} |")
    return "\n".join(lines)


def _format_cancel_comment(completed_batches: int, total_batches: int) -> str:
    return f"⏹️ Cancelled by user. Completed {completed_batches}/{total_batches} batches."


def _format_summary_comment(
    total: int,
    passed: int,
    failed: int,
    timeout: int,
    skipped: int,
    duration: float,
    completed_batches: int,
    total_batches: int,
) -> str:
    runnable = total - skipped
    rate = f"{passed / runnable * 100:.1f}%" if runnable > 0 else "N/A"
    if failed + timeout == 0:
        status = "✅ All passed"
    else:
        status = "❌ Has failures"
    lines = [
        f"📋 **Test Summary** — {status}",
        f"- Total: {total} | Passed: {passed} | Failed: {failed} | Timeout: {timeout} | Skipped: {skipped}",
        f"- Pass Rate: {rate}",
        f"- Duration: {_format_duration(duration)}",
        f"- Batches: {completed_batches}/{total_batches}",
    ]
    lines.append("- 💡 View detailed report: `youqu report --clean --serve`")
    return "\n".join(lines)


def _read_app_name(yaml_dir: Path) -> str:
    """Read app identifier from elements.yaml."""
    import yaml as _yaml
    elements_file = yaml_dir / "elements.yaml"
    if elements_file.exists():
        raw = _yaml.safe_load(elements_file.read_text(encoding="utf-8")) or {}
        if isinstance(raw, dict):
            return raw.get("app", "")
    return ""


def run_multica(
    autotest_path: str | None,
    issue_id: str,
    batch_size: int,
    case_timeout: int,
    module: str,
    tag: str,
) -> int:
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

    skipped_cases = [t for t in tests if t.get("skip")]
    runnable_tests = [t for t in tests if not t.get("skip")]

    if not runnable_tests:
        msg = f"All {len(tests)} cases are skipped. Nothing to run."
        print(msg, flush=True)
        if multica_available:
            if skipped_cases:
                _post_multica_comment(issue_id, _format_skip_comment(skipped_cases))
            _post_multica_comment(issue_id, msg)
        return 0

    test_ids = [t["id"] for t in runnable_tests]
    file_map = {t["id"]: t["file"] for t in runnable_tests}

    total_batches = (len(test_ids) + batch_size - 1) // batch_size
    app_name = _read_app_name(yaml_dir) or str(autotest)

    if multica_available:
        start_comment = _format_start_comment(
            app=app_name,
            module=module,
            tag=tag,
            total=len(tests),
            batches=total_batches,
            batch_size=batch_size,
            skipped_count=len(skipped_cases),
        )
        _post_multica_comment(issue_id, start_comment)

        if skipped_cases:
            _post_multica_comment(issue_id, _format_skip_comment(skipped_cases))

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
            failures=batch_result.get("failures"),
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

    report_root = autotest / "report"
    _merge_allure_dirs(report_root)

    elapsed = time.time() - start_time
    total_skipped = len(skipped_cases) + result.get("skipped", 0)

    if multica_available and result["status"] == "cancelled":
        comment = _format_cancel_comment(
            completed_batches=result["completed_batches"],
            total_batches=result["total_batches"],
        )
        _post_multica_comment(issue_id, comment)

    if multica_available and result["status"] != "cancelled":
        summary = _format_summary_comment(
            total=len(tests),
            passed=result["passed"],
            failed=result["failed"],
            timeout=result["timeout"],
            skipped=total_skipped,
            duration=elapsed,
            completed_batches=result["completed_batches"],
            total_batches=result["total_batches"],
        )
        _post_multica_comment(issue_id, summary)

    print(
        f"Summary: Total={len(tests)} | Passed={result['passed']} | "
        f"Failed={result['failed']} | Timeout={result['timeout']} | "
        f"Skipped={total_skipped} | Duration={_format_duration(elapsed)}",
        flush=True,
    )

    if result["status"] == "cancelled":
        return 1
    return 0 if (result["failed"] + result["timeout"]) == 0 else 1
