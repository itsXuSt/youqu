# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for src.web_spec.index."""

import yaml

from web_spec.index import INDEX_VERSION, WebSpecIndex


def _make_spec_dir(tmp_path):
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    (spec_dir / "login.yaml").write_text("""
id: login
name: 登录测试
module: 认证
feature: 登录
tags: [L1, smoke]
priority: 1
steps:
  - description: 检查
    assertions:
      - type: visible
        locator: {strategy: text, value: 欢迎}
""", encoding="utf-8")
    sub = spec_dir / "settings"
    sub.mkdir()
    (sub / "profile.yaml").write_text("""
title: 资料测试
module: 设置
tags: [L2]
steps:
  - description: 检查
    assertions:
      - type: visible
        locator: {strategy: text, value: 资料}
""", encoding="utf-8")
    return spec_dir


def test_rebuild_creates_index_and_tracks_subdirs(tmp_path):
    spec_dir = _make_spec_dir(tmp_path)
    idx = WebSpecIndex(spec_dir)

    specs = idx.rebuild()

    assert len(specs) == 2
    assert (spec_dir / "index.yaml").exists()
    files = {spec["file"] for spec in specs}
    assert files == {"login.yaml", "settings/profile.yaml"}


def test_rebuild_skips_non_web_specs(tmp_path):
    spec_dir = _make_spec_dir(tmp_path)
    (spec_dir / "elements.yaml").write_text("""
login_button:
  name: 登录
  role: push button
""", encoding="utf-8")
    (spec_dir / "test_desktop.yaml").write_text("""
name: 桌面 YAML 用例
app: deepin-example
steps:
  - action: click
    ref: login_button
""", encoding="utf-8")
    idx = WebSpecIndex(spec_dir)

    specs = idx.rebuild()

    assert len(specs) == 2
    assert {spec["file"] for spec in specs} == {"login.yaml", "settings/profile.yaml"}


def test_query_creates_missing_index(tmp_path):
    spec_dir = _make_spec_dir(tmp_path)
    idx = WebSpecIndex(spec_dir)

    specs = idx.query()

    assert len(specs) == 2
    assert idx.index_file.exists()
    raw = yaml.safe_load(idx.index_file.read_text(encoding="utf-8"))
    assert raw["version"] == INDEX_VERSION


def test_query_rebuilds_stale_index_before_filtering(tmp_path):
    spec_dir = _make_spec_dir(tmp_path)
    (spec_dir / "index.yaml").write_text("""
version: 1
specs:
  - id: elements
    file: elements.yaml
    name: elements
    tags: []
""", encoding="utf-8")
    idx = WebSpecIndex(spec_dir)

    specs = idx.query()

    assert len(specs) == 2
    assert {spec["file"] for spec in specs} == {"login.yaml", "settings/profile.yaml"}
    raw = yaml.safe_load(idx.index_file.read_text(encoding="utf-8"))
    assert raw["version"] == INDEX_VERSION


def test_query_by_module_and_tags(tmp_path):
    spec_dir = _make_spec_dir(tmp_path)
    idx = WebSpecIndex(spec_dir)
    idx.rebuild()

    assert [spec["id"] for spec in idx.query(module="认证")] == ["login"]
    assert [spec["id"] for spec in idx.query(tags=["L2"])] == ["profile"]


def test_stats(tmp_path):
    spec_dir = _make_spec_dir(tmp_path)
    idx = WebSpecIndex(spec_dir)
    stats = idx.get_stats()

    assert stats["total"] == 2
    assert stats["modules"] == {"认证": 1, "设置": 1}
    assert stats["tags"]["smoke"] == 1
