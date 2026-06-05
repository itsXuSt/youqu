# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Element registry — loads, caches, and queries elements.yaml.

elements.yaml is the mandatory, single-source-of-truth registry for UI
element references in YAML test cases.  Every test-case YAML file in the
same directory MUST have a sibling ``elements.yaml`` that defines every
element referenced via ``ref``.

Each element maps a logical alias to:

* AT-SPI selectors — ``name``, ``role``, ``accessible_id``
* Coordinates — ``x``, ``y`` (for mouse clicks)
* Menu paths — ``menu`` (list of strings, for keyboard navigation)

.. code-block:: yaml

    app: deepin-terminal
    elements:
      file_menu:          # AT-SPI element
        name: "文件"
        role: "menu"
      app_icon:           # coordinate-only (mouse right-click)
        x: 500
        y: 200
      file_open:          # keyboard menu path
        menu: ["文件", "打开"]
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ElementError(ValueError):
    """Raised when elements.yaml is missing, empty, or a ref is not found."""


def load_elements(testcase_yaml_path: Path) -> dict[str, dict[str, Any]]:
    """Load ``elements.yaml`` from the directory containing a test-case YAML.

    Args:
        testcase_yaml_path: Absolute path to a ``test_*.yaml`` file.

    Returns:
        ``{"alias": {attrs...}, ...}`` from the ``elements`` key.

    Raises:
        ElementError: ``elements.yaml`` missing or contains no elements.
    """
    elements_file = testcase_yaml_path.parent / "elements.yaml"
    if not elements_file.exists():
        raise ElementError(
            f"elements.yaml not found at {elements_file}. "
            "Every YAML test case directory must contain an elements.yaml "
            "that defines all element references used via 'ref'."
        )

    raw = yaml.safe_load(elements_file.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ElementError(
            f"elements.yaml at {elements_file} is not a valid YAML mapping."
        )

    elements: dict[str, dict[str, Any]] = raw.get("elements", {})
    if not elements:
        raise ElementError(
            f"elements.yaml at {elements_file} has no 'elements' defined."
        )

    return elements


def resolve_ref(
    ref_name: str, elements: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Look up *ref_name* in the element registry.

    Args:
        ref_name: Logical alias (key under ``elements:``).
        elements: Registry dict from :func:`load_elements`.

    Returns:
        Element attribute dict (e.g. ``{"name": "OK", "role": "push button"}``).

    Raises:
        ElementError: *ref_name* not found.
    """
    if ref_name not in elements:
        available = ", ".join(sorted(elements.keys())[:20])
        hint = f" Available: {available}" if available else " (empty)"
        raise ElementError(
            f"ref '{ref_name}' not found in elements.yaml.{hint}"
        )
    return elements[ref_name]
