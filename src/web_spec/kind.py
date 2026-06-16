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
    """Return whether a YAML file is the suite descriptor in a suite directory."""
    return Path(path).name in {"suite.yaml", "suite.yml"}


def find_suite_file(path: str | Path) -> Path | None:
    """Return the suite descriptor under a directory, if present."""
    root = Path(path)
    if root.is_file():
        return root if is_suite_file(root) else None
    for name in ("suite.yaml", "suite.yml"):
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def is_legacy_suite_file(path: str | Path) -> bool:
    """Return whether a YAML file uses the removed external suite naming."""
    return Path(path).name.endswith((".suite.yaml", ".suite.yml"))


def is_config_file(path: str | Path) -> bool:
    """Return whether a YAML file name is the conventional Web spec config file."""
    return Path(path).name in {"web_spec.yaml", "web_spec.yml"}


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
