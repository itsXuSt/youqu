# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for src.yaml_test.index."""

import pytest
from pathlib import Path

from src.yaml_test.index import YamlIndex


def _make_yaml_dir(tmp_path, files):
    """Create a yaml directory with test files and elements.yaml."""
    yaml_dir = tmp_path / "yaml"
    yaml_dir.mkdir()
    (yaml_dir / "elements.yaml").write_text("app: test\n", encoding="utf-8")
    for name, content in files.items():
        (yaml_dir / name).write_text(content, encoding="utf-8")
    return yaml_dir


class TestRebuild:
    def test_rebuild_creates_index(self, tmp_path):
        yaml_dir = _make_yaml_dir(tmp_path, {
            "test_play_001.yaml": """
name: "播放测试"
module: "播放"
feature: "本地文件"
tags: ["L1", "smoke"]
app: "deepin-music"
""",
        })
        idx = YamlIndex(yaml_dir)
        tests = idx.rebuild()
        assert len(tests) == 1
        assert tests[0]["id"] == "test_play_001"
        assert tests[0]["module"] == "播放"
        assert tests[0]["tags"] == ["L1", "smoke"]
        assert (yaml_dir / "index.yaml").exists()

    def test_rebuild_skips_elements_yaml(self, tmp_path):
        yaml_dir = _make_yaml_dir(tmp_path, {
            "test_play_001.yaml": "name: Test\napp: test\n",
        })
        idx = YamlIndex(yaml_dir)
        tests = idx.rebuild()
        ids = [t["id"] for t in tests]
        assert "elements" not in ids

    def test_rebuild_skips_corrupt_yaml(self, tmp_path):
        yaml_dir = _make_yaml_dir(tmp_path, {
            "test_good_001.yaml": "name: Good\napp: test\n",
            "test_bad_002.yaml": "\tbad: [unclosed",
        })
        idx = YamlIndex(yaml_dir)
        tests = idx.rebuild()
        assert len(tests) == 1
        assert tests[0]["id"] == "test_good_001"

    def test_rebuild_skips_non_test_yaml(self, tmp_path):
        yaml_dir = _make_yaml_dir(tmp_path, {
            "test_play_001.yaml": "name: Play\napp: test\n",
            "config.yaml": "name: NotATest\n",
        })
        idx = YamlIndex(yaml_dir)
        tests = idx.rebuild()
        assert len(tests) == 1
        assert tests[0]["id"] == "test_play_001"

    def test_rebuild_multiple_tests(self, tmp_path):
        yaml_dir = _make_yaml_dir(tmp_path, {
            "test_play_001.yaml": 'name: "播放测试"\nmodule: "播放"\napp: "music"\n',
            "test_play_002.yaml": 'name: "暂停测试"\nmodule: "播放"\napp: "music"\n',
            "test_edit_001.yaml": 'name: "编辑测试"\nmodule: "编辑"\napp: "music"\n',
        })
        idx = YamlIndex(yaml_dir)
        tests = idx.rebuild()
        assert len(tests) == 3

    def test_rebuild_defaults_for_missing_fields(self, tmp_path):
        yaml_dir = _make_yaml_dir(tmp_path, {
            "test_minimal_001.yaml": "name: Minimal\n",
        })
        idx = YamlIndex(yaml_dir)
        tests = idx.rebuild()
        assert tests[0]["module"] == ""
        assert tests[0]["feature"] == ""
        assert tests[0]["tags"] == []
        assert tests[0]["description"] == ""
        assert tests[0]["app"] == ""


class TestLoadAndAutoRebuild:
    def test_load_auto_rebuilds_when_index_missing(self, tmp_path):
        yaml_dir = _make_yaml_dir(tmp_path, {
            "test_play_001.yaml": "name: Test\napp: test\n",
        })
        idx = YamlIndex(yaml_dir)
        assert not (yaml_dir / "index.yaml").exists()
        tests = idx.load()
        assert len(tests) == 1
        assert (yaml_dir / "index.yaml").exists()

    def test_load_returns_cached_when_index_exists(self, tmp_path):
        yaml_dir = _make_yaml_dir(tmp_path, {
            "test_play_001.yaml": "name: Original\napp: test\n",
        })
        idx = YamlIndex(yaml_dir)
        idx.rebuild()
        tests = idx.load()
        assert tests[0]["name"] == "Original"


class TestQuery:
    def test_query_all(self, tmp_path):
        yaml_dir = _make_yaml_dir(tmp_path, {
            "test_a_001.yaml": 'name: "A"\napp: "app-a"\nmodule: "m1"\ntags: ["L1"]\n',
            "test_b_001.yaml": 'name: "B"\napp: "app-b"\nmodule: "m2"\ntags: ["L2"]\n',
        })
        idx = YamlIndex(yaml_dir)
        idx.rebuild()
        tests = idx.query()
        assert len(tests) == 2

    def test_query_by_app(self, tmp_path):
        yaml_dir = _make_yaml_dir(tmp_path, {
            "test_a_001.yaml": 'name: "A"\napp: "app-a"\n',
            "test_b_001.yaml": 'name: "B"\napp: "app-b"\n',
        })
        idx = YamlIndex(yaml_dir)
        idx.rebuild()
        tests = idx.query(app="app-a")
        assert len(tests) == 1
        assert tests[0]["id"] == "test_a_001"

    def test_query_by_module(self, tmp_path):
        yaml_dir = _make_yaml_dir(tmp_path, {
            "test_a_001.yaml": 'name: "A"\nmodule: "播放"\n',
            "test_b_001.yaml": 'name: "B"\nmodule: "设置"\n',
        })
        idx = YamlIndex(yaml_dir)
        idx.rebuild()
        tests = idx.query(module="播放")
        assert len(tests) == 1
        assert tests[0]["id"] == "test_a_001"

    def test_query_by_feature(self, tmp_path):
        yaml_dir = _make_yaml_dir(tmp_path, {
            "test_a_001.yaml": 'name: "A"\nfeature: "本地文件"\n',
            "test_b_001.yaml": 'name: "B"\nfeature: "在线流"\n',
        })
        idx = YamlIndex(yaml_dir)
        idx.rebuild()
        tests = idx.query(feature="本地文件")
        assert len(tests) == 1

    def test_query_by_tags(self, tmp_path):
        yaml_dir = _make_yaml_dir(tmp_path, {
            "test_a_001.yaml": 'name: "A"\ntags: ["L1", "smoke"]\n',
            "test_b_001.yaml": 'name: "B"\ntags: ["L2"]\n',
        })
        idx = YamlIndex(yaml_dir)
        idx.rebuild()
        tests = idx.query(tags=["L1"])
        assert len(tests) == 1
        assert tests[0]["id"] == "test_a_001"

    def test_query_by_multiple_tags_and(self, tmp_path):
        yaml_dir = _make_yaml_dir(tmp_path, {
            "test_a_001.yaml": 'name: "A"\ntags: ["L1", "smoke"]\n',
            "test_b_001.yaml": 'name: "B"\ntags: ["L2", "smoke"]\n',
        })
        idx = YamlIndex(yaml_dir)
        idx.rebuild()
        tests = idx.query(tags=["smoke"])
        assert len(tests) == 2
        tests = idx.query(tags=["L1", "smoke"])
        assert len(tests) == 1
        assert tests[0]["id"] == "test_a_001"

    def test_query_empty_result(self, tmp_path):
        yaml_dir = _make_yaml_dir(tmp_path, {
            "test_a_001.yaml": 'name: "A"\napp: "app-a"\n',
        })
        idx = YamlIndex(yaml_dir)
        idx.rebuild()
        tests = idx.query(app="nonexistent")
        assert len(tests) == 0

    def test_query_combined_and(self, tmp_path):
        yaml_dir = _make_yaml_dir(tmp_path, {
            "test_a_001.yaml": 'name: "A"\napp: "app-a"\nmodule: "m1"\ntags: ["L1"]\n',
            "test_b_001.yaml": 'name: "B"\napp: "app-a"\nmodule: "m2"\ntags: ["L2"]\n',
            "test_c_001.yaml": 'name: "C"\napp: "app-b"\nmodule: "m1"\ntags: ["L1"]\n',
        })
        idx = YamlIndex(yaml_dir)
        idx.rebuild()
        tests = idx.query(app="app-a", module="m1", tags=["L1"])
        assert len(tests) == 1
        assert tests[0]["id"] == "test_a_001"


class TestStats:
    def test_stats_empty(self, tmp_path):
        yaml_dir = _make_yaml_dir(tmp_path, {})
        idx = YamlIndex(yaml_dir)
        stats = idx.get_stats()
        assert stats["total"] == 0
        assert stats["modules"] == {}
        assert stats["tags"] == {}

    def test_stats_with_data(self, tmp_path):
        yaml_dir = _make_yaml_dir(tmp_path, {
            "test_a_001.yaml": 'name: "A"\nmodule: "播放"\ntags: ["L1", "smoke"]\n',
            "test_b_001.yaml": 'name: "B"\nmodule: "播放"\ntags: ["L1"]\n',
            "test_c_001.yaml": 'name: "C"\nmodule: "设置"\ntags: ["L2"]\n',
        })
        idx = YamlIndex(yaml_dir)
        idx.rebuild()
        stats = idx.get_stats()
        assert stats["total"] == 3
        assert stats["modules"]["播放"] == 2
        assert stats["modules"]["设置"] == 1
        assert stats["tags"]["L1"] == 2
        assert stats["tags"]["smoke"] == 1
        assert stats["tags"]["L2"] == 1

    def test_stats_uncategorized_excluded(self, tmp_path):
        yaml_dir = _make_yaml_dir(tmp_path, {
            "test_a_001.yaml": 'name: "A"\n',
        })
        idx = YamlIndex(yaml_dir)
        idx.rebuild()
        stats = idx.get_stats()
        assert stats["total"] == 1
        assert stats["modules"] == {}
