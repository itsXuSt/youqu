# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable

_cancelled = False


def _on_sigterm(signum: int, frame: object) -> None:
    global _cancelled
    _cancelled = True


def install_sigterm_handler() -> None:
    signal.signal(signal.SIGTERM, _on_sigterm)


def _parse_junit_xml(xml_path: Path) -> dict:
    """Parse pytest --junitxml output for structured test results.

    Returns:
        {"passed": int, "failed": int, "skipped": int,
         "errors": {test_name: message}}
    """
    result = {"passed": 0, "failed": 0, "skipped": 0, "errors": {}}
    if not xml_path.exists():
        return result

    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return result

    for tc in tree.findall(".//testcase"):
        fail_el = tc.find("failure")
        skip_el = tc.find("skipped")
        if fail_el is not None:
            result["failed"] += 1
            name = tc.get("name", "")
            msg = fail_el.get("message", "") or fail_el.text or ""
            result["errors"][name] = msg[:500]
        elif skip_el is not None:
            result["skipped"] += 1
        else:
            result["passed"] += 1

    return result


def _merge_allure_dirs(report_root: Path) -> Path:
    target = report_root / "allure_raw"
    target.mkdir(parents=True, exist_ok=True)
    for batch_dir in report_root.glob("batch_*"):
        if not batch_dir.is_dir():
            continue
        for case_dir in batch_dir.glob("case_*"):
            if not case_dir.is_dir():
                continue
            for item in case_dir.iterdir():
                if item.suffix != ".json":
                    continue
                dest = target / item.name
                if not dest.exists():
                    shutil.copy2(item, dest)
    return target


def run_batches(
    test_ids: list[str],
    yaml_dir: str | Path,
    pytest_ini_dir: str | Path,
    batch_size: int = 20,
    case_timeout: int = 90,
    per_batch_callback: Callable[[dict], None] | None = None,
    per_case_callback: Callable[[dict], None] | None = None,
    cancel_event: threading.Event | None = None,
    file_map: dict[str, str] | None = None,
) -> dict:
    global _cancelled
    _cancelled = False  # Reset signal state on entry
    yaml_dir = Path(yaml_dir)
    pytest_ini_dir = Path(pytest_ini_dir)
    total = len(test_ids)

    if total == 0:
        return {
            "status": "completed",
            "passed": 0,
            "failed": 0,
            "timeout": 0,
            "skipped": 0,
            "total": 0,
            "completed_batches": 0,
            "total_batches": 0,
            "batches": [],
        }

    batches = [test_ids[i:i + batch_size] for i in range(0, total, batch_size)]
    results: list[dict] = []
    total_passed = 0
    total_failed = 0
    total_timeout = 0
    total_skipped = 0
    cases_done = 0

    for idx, batch in enumerate(batches):
        if cancel_event and cancel_event.is_set():
            return {
                "status": "cancelled",
                "passed": total_passed,
                "failed": total_failed,
                "timeout": total_timeout,
                "skipped": total_skipped,
                "total": total,
                "completed_batches": idx,
                "total_batches": len(batches),
                "batches": results,
            }

        if _cancelled:
            return {
                "status": "cancelled",
                "passed": total_passed,
                "failed": total_failed,
                "timeout": total_timeout,
                "skipped": total_skipped,
                "total": total,
                "completed_batches": idx,
                "total_batches": len(batches),
                "batches": results,
            }

        batch_passed = 0
        batch_failed = 0
        batch_timeout = 0
        batch_skipped = 0
        batch_failures: list[dict] = []

        for test_id in batch:
            if file_map:
                yaml_file = str(yaml_dir / file_map.get(test_id, f"{test_id}.yaml"))
            else:
                yaml_file = str(yaml_dir / f"{test_id}.yaml")

            allure_dir = pytest_ini_dir / "report" / f"batch_{idx+1}" / f"case_{test_id}"
            allure_dir.mkdir(parents=True, exist_ok=True)
            junit_path = pytest_ini_dir / "report" / f"batch_{idx+1}" / f"{test_id}.xml"

            cmd = [
                sys.executable, "-m", "pytest",
                "-c", str(pytest_ini_dir / "pytest.ini"),
                "--rootdir", str(pytest_ini_dir),
                "-q", "--tb=short",
                "--alluredir", str(allure_dir),
                f"--junitxml={junit_path}",
                yaml_file,
            ]

            case_result = {
                "test_id": test_id,
                "passed": 0,
                "failed": 0,
                "timeout": 0,
                "skipped": 0,
                "error": "",
            }

            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                )
                try:
                    proc.communicate(timeout=case_timeout)
                    parsed = _parse_junit_xml(junit_path)
                    if proc.returncode != 0:
                        if parsed["failed"] > 0:
                            case_result["failed"] = parsed["failed"]
                            case_result["passed"] = parsed["passed"]
                            batch_failed += parsed["failed"]
                            batch_passed += parsed["passed"]
                        elif parsed["passed"] > 0:
                            case_result["passed"] = parsed["passed"]
                            batch_passed += parsed["passed"]
                        else:
                            case_result["failed"] = 1
                            batch_failed += 1
                    elif parsed["passed"] > 0:
                        case_result["passed"] = parsed["passed"]
                        batch_passed += parsed["passed"]
                    else:
                        skipped = parsed["skipped"] if parsed["skipped"] > 0 else 1
                        case_result["skipped"] = skipped
                        batch_skipped += skipped
                except subprocess.TimeoutExpired:
                    proc.terminate()  # SIGTERM per PRD 9.1
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()  # SIGKILL fallback
                    case_result["timeout"] = 1
                    batch_timeout += 1
            except (OSError, ValueError):
                parsed = {"errors": {}}
                case_result["failed"] = 1
                case_result["error"] = "Process execution error"
                batch_failed += 1

            if case_result["failed"] > 0 and not case_result["error"]:
                case_result["error"] = "; ".join(parsed["errors"].values())[:500]

            if case_result["timeout"] > 0:
                case_result["error"] = f"Timeout after {case_timeout}s"

            if case_result["error"]:
                print(
                    f"[youqu] {test_id}: {case_result['error']}",
                    file=sys.stderr, flush=True,
                )

            if case_result["failed"] > 0 or case_result["timeout"] > 0:
                batch_failures.append({
                    "test_id": test_id,
                    "error": case_result["error"],
                })

            cases_done += 1
            if cases_done % 10 == 0:
                print(f"[youqu] case {cases_done}/{total} done", flush=True)

            if per_case_callback:
                per_case_callback(case_result)

        total_passed += batch_passed
        total_failed += batch_failed
        total_timeout += batch_timeout
        total_skipped += batch_skipped

        batch_result = {
            "batch": idx + 1,
            "passed": batch_passed,
            "failed": batch_failed,
            "timeout": batch_timeout,
            "skipped": batch_skipped,
            "cases": list(batch),
            "failures": batch_failures,
        }
        results.append(batch_result)

        if per_batch_callback:
            per_batch_callback(batch_result)

    all_failures = []
    for b in results:
        all_failures.extend(b.get("failures", []))

    return {
        "status": "completed",
        "passed": total_passed,
        "failed": total_failed,
        "timeout": total_timeout,
        "skipped": total_skipped,
        "total": total,
        "completed_batches": len(batches),
        "total_batches": len(batches),
        "batches": results,
        "failures": all_failures,
    }
