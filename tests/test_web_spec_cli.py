# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for cli.web_spec."""

from argparse import Namespace

import pytest

from cli.web_spec import run


def test_web_spec_init_config(tmp_path, capsys):
    config_path = tmp_path / "web_spec.yaml"
    args = Namespace(
        web_spec_command="init",
        config_path=str(config_path),
        force=False,
    )

    run(args)

    captured = capsys.readouterr()
    assert "Web spec config created" in captured.out
    assert "base_url: http://localhost:5173" in config_path.read_text(encoding="utf-8")


def test_web_spec_init_config_refuses_existing_file(tmp_path, capsys):
    config_path = tmp_path / "web_spec.yaml"
    config_path.write_text("base_url: old\n", encoding="utf-8")
    args = Namespace(
        web_spec_command="init",
        config_path=str(config_path),
        force=False,
    )

    with pytest.raises(SystemExit) as exc_info:
        run(args)

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert "--force" in captured.err
    assert config_path.read_text(encoding="utf-8") == "base_url: old\n"


def test_web_spec_run_auto_discovers_config(tmp_path, monkeypatch):
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
    (tmp_path / "web_spec.yaml").write_text("""
base_url: http://example.test
entry_route: /chat
""", encoding="utf-8")
    seen = {}

    class FakeRunner:
        def __init__(self, config, reporter=None):
            seen["base_url"] = config.base_url
            seen["entry_route"] = config.entry_route

        def run_all(self, specs, report_dir=None):
            from web_spec.result import SuiteRecord
            suite = SuiteRecord()
            suite.finalize()
            return suite

    monkeypatch.setattr("web_spec.runner.WebSpecRunner", FakeRunner)
    args = Namespace(
        web_spec_command="run",
        spec_path=str(spec_path),
        config=None,
        headed=False,
        report_dir=None,
        dry_run=False,
        no_screenshot=False,
        verbose=False,
    )

    run(args)

    assert seen == {"base_url": "http://example.test", "entry_route": "/chat"}


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


def test_web_spec_suite_auto_discovers_config(tmp_path, monkeypatch):
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
    (tmp_path / "web_spec.yaml").write_text("""
base_url: http://example.test
entry_route: /suite
""", encoding="utf-8")
    seen = {}

    class FakeRunner:
        def __init__(self, config, reporter=None):
            seen["base_url"] = config.base_url
            seen["entry_route"] = config.entry_route

        def run_suite(self, suite_spec, report_dir=None):
            from web_spec.result import SuiteRecord
            suite = SuiteRecord(suite_id=suite_spec.id, suite_name=suite_spec.name)
            suite.finalize()
            return suite

    monkeypatch.setattr("web_spec.runner.WebSpecRunner", FakeRunner)
    args = Namespace(
        web_spec_command="suite",
        suite_path=str(suite_path),
        config=None,
        headed=False,
        report_dir=None,
        dry_run=False,
        no_screenshot=False,
        verbose=False,
    )

    run(args)

    assert seen == {"base_url": "http://example.test", "entry_route": "/suite"}


def test_web_spec_suite_dry_run(tmp_path, capsys):
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

    args = Namespace(
        web_spec_command="suite",
        suite_path=str(suite_path),
        config=None,
        headed=False,
        report_dir=None,
        dry_run=True,
        no_screenshot=False,
        verbose=False,
    )

    run(args)

    captured = capsys.readouterr()
    assert "[DRY-RUN] suite smoke: 冒烟套件" in captured.out
    assert "login" in captured.out
    assert "共 1 个 spec" in captured.out


def test_web_spec_run_rejects_suite_file(tmp_path, capsys):
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
specs:
  - login.yaml
""", encoding="utf-8")

    args = Namespace(
        web_spec_command="run",
        spec_path=str(suite_path),
        config=None,
        headed=False,
        report_dir=None,
        dry_run=True,
        no_screenshot=False,
    )

    with pytest.raises(SystemExit) as exc_info:
        run(args)

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert "youqu web-spec suite" in captured.err


def test_web_spec_suite_rejects_case_file(tmp_path, capsys):
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
        web_spec_command="suite",
        suite_path=str(spec_path),
        config=None,
        headed=False,
        report_dir=None,
        dry_run=True,
        no_screenshot=False,
        verbose=False,
    )

    with pytest.raises(SystemExit) as exc_info:
        run(args)

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert "youqu web-spec run" in captured.err


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
