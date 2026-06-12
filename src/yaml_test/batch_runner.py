# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable

_cancelled = False


def _on_sigterm(signum: int, frame: object) -> None:
    global _cancelled
    _cancelled = True


def install_sigterm_handler() -> None:
    signal.signal(signal.SIGTERM, _on_sigterm)


def _parse_pytest_output(output: str) -> dict:
    passed = failed = skipped = 0
    for line in output.splitlines():
        line = line.strip()
        m = re.search(r"(\d+)\s+passed", line)
        if m:
            passed = int(m.group(1))
            m2 = re.search(r"(\d+)\s+failed", line)
            if m2:
                failed = int(m2.group(1))
            m3 = re.search(r"(\d+)\s+skipped", line)
            if m3:
                skipped = int(m3.group(1))
    return {"passed": passed, "failed": failed, "skipped": skipped}


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

        for test_id in batch:
            if file_map:
                yaml_file = str(yaml_dir / file_map.get(test_id, f"{test_id}.yaml"))
            else:
                yaml_file = str(yaml_dir / f"{test_id}.yaml")

            allure_dir = pytest_ini_dir / "report" / f"batch_{idx+1}" / f"case_{test_id}"
            allure_dir.mkdir(parents=True, exist_ok=True)

            cmd = [
                sys.executable, "-m", "pytest",
                "-c", str(pytest_ini_dir / "pytest.ini"),
                "--rootdir", str(pytest_ini_dir),
                "-q", "--tb=short",
                "--alluredir", str(allure_dir),
                yaml_file,
            ]

            case_result = {
                "test_id": test_id,
                "passed": 0,
                "failed": 0,
                "timeout": 0,
                "skipped": 0,
            }

            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                )
                try:
                    stdout, stderr = proc.communicate(timeout=case_timeout)
                    parsed = _parse_pytest_output(stdout)
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
                case_result["failed"] = 1
                batch_failed += 1

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
        }
        results.append(batch_result)

        if per_batch_callback:
            per_batch_callback(batch_result)

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
    }
