# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only

import fcntl
import os
import sys
from pathlib import Path

_DEFAULT_REPORT_DIR = "report"
_LOCK_FILE = "/tmp/youqu-test.lock"


def _find_autotest_dir(override=None):
    if override:
        p = Path(override).resolve()
        if not p.exists():
            print(f"Error: {p} does not exist")
            sys.exit(1)
        return p

    cwd = Path.cwd()
    if (cwd / "autotest").is_dir():
        return cwd / "autotest"
    if (cwd / "case").is_dir() and (cwd / "pytest.ini").exists():
        return cwd
    if (cwd / "pytest.ini").exists() or (cwd / "report").is_dir():
        return cwd

    print("Error: No autotest/ directory found. Run 'youqu make <name>' first.")
    sys.exit(1)


def _acquire_test_lock():
    """Acquire exclusive lock to prevent concurrent test execution."""
    lock_fd = open(_LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_fd
    except BlockingIOError:
        print("Error: Another youqu test is already running. Exiting.", flush=True)
        sys.exit(1)


def run(
    autotest_path=None,
    extra=None,
    multica_report=False,
    issue_id="",
    batch_size=20,
    case_timeout=90,
    module="",
    tag="",
):
    extra = extra or []
    lock_fd = _acquire_test_lock()

    try:
        autotest = _find_autotest_dir(autotest_path)

        if multica_report:
            for i, arg in enumerate(extra):
                if arg == "-k":
                    print("Error: -k filtering is not supported in multica mode.", flush=True)
                    sys.exit(1)

            from cli.multica_report import run_multica
            exit_code = run_multica(
                autotest_path=str(autotest),
                issue_id=issue_id,
                batch_size=batch_size,
                case_timeout=case_timeout,
                module=module,
                tag=tag,
            )
            sys.exit(exit_code)

        pytest_args = [
            "-c", str(autotest / "pytest.ini"),
            "--rootdir", str(autotest),
        ]

        if not any("--alluredir" in a for a in extra):
            report_dir = autotest / _DEFAULT_REPORT_DIR
            report_dir.mkdir(parents=True, exist_ok=True)
            pytest_args.extend(["--alluredir", str(report_dir)])

        pytest_args.extend(extra)

        import pytest

        os.chdir(str(autotest))
        sys.exit(pytest.main(pytest_args))
    finally:
        try:
            lock_fd.close()
        except Exception:
            pass
