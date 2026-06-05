# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only

import os
import sys
from pathlib import Path

_DEFAULT_REPORT_DIR = "report"


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

    print("Error: No autotest/ directory found. Run 'youqu make <name>' first.")
    sys.exit(1)


def run(autotest_path=None, extra=None):
    extra = extra or []
    autotest = _find_autotest_dir(autotest_path)

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
