# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for src.yaml_test.elements — element registry loading."""

import pytest

from src.yaml_test.elements import ElementError, load_elements


def _write_elements(dir_, content="app: test\nelements:\n  ok:\n    name: OK\n"):
    p = dir_ / "elements.yaml"
    p.write_text(content, encoding="utf-8")
    return p


def _write_test_yaml(dir_, name="test_case_001.yaml", content=None):
    if content is None:
        content = "name: test\n"
    p = dir_ / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


class TestLoadElementsFlat:
    """Flat directory — backward-compatible behavior."""

    def test_load_from_same_dir(self, tmp_path):
        _write_elements(tmp_path)
        test_yaml = _write_test_yaml(tmp_path)
        elements = load_elements(test_yaml)
        assert elements["ok"]["name"] == "OK"

    def test_missing_raises(self, tmp_path):
        test_yaml = _write_test_yaml(tmp_path)
        with pytest.raises(ElementError, match="elements.yaml not found"):
            load_elements(test_yaml)

    def test_empty_elements_raises(self, tmp_path):
        _write_elements(tmp_path, "app: test\nelements:\n")
        test_yaml = _write_test_yaml(tmp_path)
        with pytest.raises(ElementError, match="no 'elements' defined"):
            load_elements(test_yaml)

    def test_non_mapping_raises(self, tmp_path):
        _write_elements(tmp_path, "- item1\n- item2\n")
        test_yaml = _write_test_yaml(tmp_path)
        with pytest.raises(ElementError, match="not a valid YAML mapping"):
            load_elements(test_yaml)


class TestLoadElementsUpward:
    """Upward search supports subdirectory organization."""

    def test_find_in_parent(self, tmp_path):
        """elements.yaml at yaml/ root, test at yaml/module/."""
        yaml_root = tmp_path / "yaml"
        yaml_root.mkdir()
        _write_elements(yaml_root)

        module_dir = yaml_root / "module"
        module_dir.mkdir()
        test_yaml = _write_test_yaml(module_dir)

        elements = load_elements(test_yaml)
        assert elements["ok"]["name"] == "OK"

    def test_find_two_levels_up(self, tmp_path):
        """elements.yaml at yaml/, test at yaml/a/b/."""
        yaml_root = tmp_path / "yaml"
        yaml_root.mkdir()
        _write_elements(yaml_root)

        deep = yaml_root / "a" / "b"
        deep.mkdir(parents=True)
        test_yaml = _write_test_yaml(deep)

        elements = load_elements(test_yaml)
        assert elements["ok"]["name"] == "OK"

    def test_find_at_four_levels(self, tmp_path):
        """elements.yaml at root, test at /a/b/c/d/ (4 levels up)."""
        _write_elements(tmp_path)

        deep = tmp_path / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True)
        test_yaml = _write_test_yaml(deep)

        elements = load_elements(test_yaml, max_depth=4)
        assert elements["ok"]["name"] == "OK"

    def test_exceeds_max_depth_raises(self, tmp_path):
        """elements.yaml 5 levels up should not be found with max_depth=4."""
        _write_elements(tmp_path)

        deep = tmp_path / "a" / "b" / "c" / "d" / "e"
        deep.mkdir(parents=True)
        test_yaml = _write_test_yaml(deep)

        with pytest.raises(ElementError, match="elements.yaml not found"):
            load_elements(test_yaml, max_depth=4)

    def test_nonexistent_raises_with_searched_paths(self, tmp_path):
        yaml_root = tmp_path / "yaml"
        yaml_root.mkdir()
        test_yaml = _write_test_yaml(yaml_root)

        with pytest.raises(ElementError) as exc_info:
            load_elements(test_yaml)
        # Error message should include searched paths
        assert "searched" in str(exc_info.value)

    def test_closest_elements_wins(self, tmp_path):
        """When elements.yaml exists at multiple levels, closest to test wins."""
        yaml_root = tmp_path / "yaml"
        yaml_root.mkdir()
        _write_elements(yaml_root, "app: root\nelements:\n  el:\n    name: root\n")

        module_dir = yaml_root / "module"
        module_dir.mkdir()
        _write_elements(module_dir, "app: module\nelements:\n  el:\n    name: module\n")

        test_yaml = _write_test_yaml(module_dir)
        elements = load_elements(test_yaml)
        assert elements["el"]["name"] == "module"
