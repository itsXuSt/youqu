# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for src.web_spec.loader."""

import pytest

from web_spec.loader import SpecValidationError, load_spec, load_spec_dir, load_specs


def _write_spec(path, title="登录测试"):
    path.write_text(f"""
id: {path.stem}
title: {title}
module: 认证
feature: 登录
tags: [smoke]
steps:
  - description: 点击登录
    actions:
      - type: click
        locator: {{strategy: role, value: button, name: 登录}}
    assertions:
      - type: visible
        locator: {{strategy: text, value: 欢迎}}
""", encoding="utf-8")
    return path


def test_load_spec_parses_yaml(tmp_path):
    spec_path = _write_spec(tmp_path / "login.yaml")
    spec = load_spec(spec_path)

    assert spec.id == "login"
    assert spec.title == "登录测试"
    assert spec.module == "认证"
    assert spec.source == str(spec_path)
    assert spec.steps[0].order == 1


def test_load_spec_uses_name_as_title(tmp_path):
    spec_path = tmp_path / "named.yaml"
    spec_path.write_text("""
name: 命名用例
steps:
  - description: 等待文本
    assertions:
      - type: visible
        locator: {strategy: text, value: 完成}
""", encoding="utf-8")

    spec = load_spec(spec_path)
    assert spec.id == "named"
    assert spec.title == "命名用例"


def test_load_spec_rejects_empty_file(tmp_path):
    spec_path = tmp_path / "empty.yaml"
    spec_path.write_text("", encoding="utf-8")

    with pytest.raises(SpecValidationError):
        load_spec(spec_path)


def test_load_spec_rejects_steps_without_work(tmp_path):
    spec_path = tmp_path / "bad.yaml"
    spec_path.write_text("""
title: 无动作
steps:
  - description: 空步骤
""", encoding="utf-8")

    with pytest.raises(SpecValidationError):
        load_spec(spec_path)


def test_load_spec_dir_loads_recursively_and_skips_index(tmp_path):
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    _write_spec(spec_dir / "b.yaml", title="B")
    sub = spec_dir / "sub"
    sub.mkdir()
    _write_spec(sub / "a.yml", title="A")
    (spec_dir / "index.yaml").write_text("specs: []\n", encoding="utf-8")

    specs = load_spec_dir(spec_dir)
    assert [spec.id for spec in specs] == ["b", "a"]


def test_load_specs_accepts_file_or_directory(tmp_path):
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    spec_path = _write_spec(spec_dir / "one.yaml")

    assert len(load_specs(spec_path)) == 1
    assert len(load_specs(spec_dir)) == 1
