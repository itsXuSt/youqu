# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""CLI smoke tests for youqu web-spec."""

import os
import subprocess
import sys
from pathlib import Path


def test_youqu_web_spec_suite_dry_run_smoke(tmp_path):
    spec_path = tmp_path / "login.yaml"
    spec_path.write_text("""
id: login
title: 登录测试
steps:
  - description: 检查
    assertions:
      - type: visible
        locator: {strategy: text, value: 欢迎}
""", encoding="utf-8")
    suite_path = tmp_path / "smoke.suite.yaml"
    suite_path.write_text("""
id: smoke
name: 冒烟套件
specs:
  - login.yaml
""", encoding="utf-8")

    project_parent = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{project_parent / 'youqu' / 'src'}:{project_parent}"
    result = subprocess.run(
        [sys.executable, "-m", "youqu.cli.main", "web-spec", "suite", str(suite_path), "--dry-run"],
        cwd=project_parent,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0
    assert "[DRY-RUN] suite smoke: 冒烟套件" in result.stdout


def test_youqu_web_spec_dry_run_smoke(tmp_path):
    spec_path = tmp_path / "login.yaml"
    spec_path.write_text("""
id: login
title: 登录测试
steps:
  - description: 检查
    assertions:
      - type: visible
        locator: {strategy: text, value: 欢迎}
""", encoding="utf-8")

    project_parent = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{project_parent / 'youqu' / 'src'}:{project_parent}"
    result = subprocess.run(
        [sys.executable, "-m", "youqu.cli.main", "web-spec", "run", str(spec_path), "--dry-run"],
        cwd=project_parent,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0
    assert "[DRY-RUN] login: 登录测试" in result.stdout
