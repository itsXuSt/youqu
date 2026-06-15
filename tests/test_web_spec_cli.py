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


def test_web_spec_check_reports_warnings(tmp_path, capsys):
    spec_path = tmp_path / "fragile.yaml"
    spec_path.write_text("""
title: 脆弱选择器
steps:
  - description: 检查
    actions:
      - type: wait_for
        timeout_ms: 20000
    assertions:
      - type: visible
        locator: {strategy: css, value: "div > div > div .item:nth-child(1)"}
""", encoding="utf-8")

    args = Namespace(
        web_spec_command="check",
        spec_path=str(spec_path),
    )

    run(args)

    captured = capsys.readouterr()
    assert "Web spec check: checked=1" in captured.out
    assert "[WARN]" in captured.out
    assert "selector" in captured.out


def test_web_spec_list_filters_specs(tmp_path, capsys):
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    (spec_dir / "login.yaml").write_text("""
id: login
title: 登录测试
module: 认证
tags: [smoke]
steps:
  - description: 检查
    assertions:
      - type: visible
        locator: {strategy: text, value: 欢迎}
""", encoding="utf-8")
    (spec_dir / "profile.yaml").write_text("""
id: profile
title: 资料测试
module: 设置
tags: [slow]
steps:
  - description: 检查
    assertions:
      - type: visible
        locator: {strategy: text, value: 资料}
""", encoding="utf-8")

    args = Namespace(
        web_spec_command="list",
        spec_dir=str(spec_dir),
        module="认证",
        feature=None,
        tag="smoke",
    )

    run(args)

    captured = capsys.readouterr()
    assert "Specs: 1" in captured.out
    assert "login" in captured.out
    assert "profile" not in captured.out
