# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for cli.web_spec."""

from argparse import Namespace

from cli.web_spec import run


def test_web_spec_run_dry_run(tmp_path, capsys):
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

    args = Namespace(
        web_spec_command="run",
        spec_path=str(spec_path),
        config=None,
        headed=False,
        report_dir=None,
        dry_run=True,
        no_screenshot=False,
    )

    run(args)

    captured = capsys.readouterr()
    assert "[DRY-RUN] login: 登录测试" in captured.out
    assert "共 1 个 spec" in captured.out
