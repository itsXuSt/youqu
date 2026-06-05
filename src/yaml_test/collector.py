# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Pytest collection hook for YAML test case files.

Activates only when pytest.ini contains ``yaml_files`` option:
    [pytest]
    yaml_files = yaml

Files under configured directories with ``.yaml`` suffix are collected
as YamlItem instances, bypassing root conftest.py CSV/PMS hooks.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.yaml_test.parser import TestCase, parse_testcase


class YamlTestError(Exception):
    """Raised when a YAML test case execution fails."""


def pytest_collect_file(parent, file_path: Path):
    """Collect .yaml files from configured yaml_dirs only."""
    yaml_dirs = parent.config.getini("yaml_files")
    if not yaml_dirs:
        return None

    if file_path.suffix != ".yaml":
        return None

    for d in yaml_dirs:
        yaml_dir = parent.config.rootpath / d
        try:
            file_path.relative_to(yaml_dir)
            return YamlFile.from_parent(parent, path=file_path)
        except ValueError:
            continue
    return None


class YamlFile(pytest.File):
    """Represents a YAML test case file."""

    def collect(self):
        testcase = parse_testcase(self.path)
        yield YamlItem.from_parent(
            self, name=testcase.name, testcase=testcase
        )


class YamlItem(pytest.Item):
    """Represents a single YAML test case for pytest execution."""

    def __init__(self, name, parent, testcase: TestCase):
        super().__init__(name, parent)
        self.testcase = testcase

    def runtest(self):
        from src.yaml_test.executor import StepExecutor

        result = StepExecutor(self.testcase).run()
        if not result.passed:
            raise YamlTestError(result.message)

    def repr_failure(self, excinfo, style=None):
        if isinstance(excinfo.value, YamlTestError):
            return str(excinfo.value)
        return super().repr_failure(excinfo, style=style)

    def reportinfo(self):
        return self.path, 0, f"YAML: {self.testcase.name}"
