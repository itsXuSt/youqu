# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""YAML test execution engine for YouQu framework.

Collects .yaml test case files via pytest hooks and executes them
using YouQu's existing API (DogtailUtils, MouseKey, AssertCommon, etc).
"""

from src.yaml_test.collector import YamlFile, YamlItem, YamlTestError

__all__ = ["YamlFile", "YamlItem", "YamlTestError"]
