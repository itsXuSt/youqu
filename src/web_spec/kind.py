# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Detect Web YAML file kinds."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any


class WebSpecFileKind(str, Enum):
    """Supported Web YAML file kinds."""

    CASE = "case"
    SUITE = "suite"
    UNKNOWN = "unknown"
    INVALID = "invalid"


def is_suite_file(path: str | Path) -> bool:
    """Return whether a YAML file name follows the suite naming convention."""
    name = Path(path).name
    return name in {"suite.yaml", "suite.yml"} or name.endswith((".suite.yaml", ".suite.yml"))


def detect_web_spec_kind(raw: dict[str, Any]) -> WebSpecFileKind:
    """Detect whether a parsed YAML mapping is a case, suite, unknown or invalid file."""
    has_steps = "steps" in raw
    has_specs = "specs" in raw
    if has_steps and has_specs:
        return WebSpecFileKind.INVALID
    if has_specs:
        return WebSpecFileKind.SUITE
    if has_steps:
        return WebSpecFileKind.CASE
    return WebSpecFileKind.UNKNOWN
