# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for src.web_spec.suite."""

import pytest

from web_spec.loader import SpecValidationError, load_spec_dir
from web_spec.suite import load_suite


def _write_spec(path, title="登录测试"):
    path.write_text(f"""
id: {path.stem}
title: {title}
steps:
  - description: 检查
    assertions:
      - type: visible
        locator: {{strategy: text, value: 完成, exact: true}}
""", encoding="utf-8")
    return path


def test_load_suite_parses_metadata_and_relative_specs(tmp_path):
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    _write_spec(spec_dir / "login.yaml", "登录测试")
    _write_spec(spec_dir / "chat.yaml", "聊天测试")
    suite_path = tmp_path / "smoke.suite.yaml"
    suite_path.write_text("""
id: smoke
name: 冒烟套件
module: AI 助手
tags: [smoke, web]
timeout: 600
fast_fail: true
setup:
  - type: wait_for
    timeout_ms: 100
specs:
  - specs/login.yaml
  - path: specs/chat.yaml
teardown:
  steps:
    - type: press_key
      key: Escape
""", encoding="utf-8")

    suite = load_suite(suite_path)

    assert suite.id == "smoke"
    assert suite.name == "冒烟套件"
    assert suite.module == "AI 助手"
    assert suite.tags == ["smoke", "web"]
    assert suite.timeout == 600
    assert suite.fast_fail is True
    assert len(suite.setup) == 1
    assert [spec.id for spec in suite.specs] == ["login", "chat"]
    assert suite.teardown.steps[0].key == "Escape"


def test_load_suite_requires_suite_naming(tmp_path):
    _write_spec(tmp_path / "login.yaml")
    suite_path = tmp_path / "smoke.yaml"
    suite_path.write_text("""
title: 错误命名
specs:
  - login.yaml
""", encoding="utf-8")

    with pytest.raises(SpecValidationError, match="suite 文件名"):
        load_suite(suite_path)


def test_load_suite_rejects_case_file(tmp_path):
    spec_path = _write_spec(tmp_path / "login.yaml")

    with pytest.raises(SpecValidationError, match="普通 Web Spec"):
        load_suite(spec_path)


def test_load_suite_rejects_mixed_steps_and_specs(tmp_path):
    suite_path = tmp_path / "bad.suite.yaml"
    suite_path.write_text("""
specs: []
steps: []
""", encoding="utf-8")

    with pytest.raises(SpecValidationError, match="不能同时包含"):
        load_suite(suite_path)


def test_load_spec_dir_skips_suite_files(tmp_path):
    _write_spec(tmp_path / "login.yaml")
    (tmp_path / "smoke.suite.yaml").write_text("""
specs:
  - login.yaml
""", encoding="utf-8")

    specs = load_spec_dir(tmp_path)

    assert [spec.id for spec in specs] == ["login"]
