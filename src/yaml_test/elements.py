# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Element registry — loads, caches, and queries elements.yaml.

elements.yaml is the mandatory, single-source-of-truth registry for UI
element references in YAML test cases.  Test-case YAML files may be
organized into subdirectories; ``load_elements()`` searches upward from
the test file's directory up to 4 levels to find a shared ``elements.yaml``
at the ``yaml/`` root.

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

Directory layout example::

    yaml/
    ├── elements.yaml          # shared element registry
    ├── keyboard/
    │   ├── test_kb_menu_019.yaml
    │   └── test_kb_shortcut_028.yaml
    └── remote/
        ├── test_remote_add_057.yaml
        └── test_remote_edit_058.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ElementError(ValueError):
    """Raised when elements.yaml is missing, empty, or a ref is not found."""


def load_elements(
    testcase_yaml_path: Path, max_depth: int = 4
) -> dict[str, dict[str, Any]]:
    """Load ``elements.yaml`` by searching upward from the test-case YAML.

    Searches from ``testcase_yaml_path.parent`` upward up to *max_depth*
    directory levels for a shared ``elements.yaml``.  This supports
    organizing test cases into subdirectories while keeping a single
    element registry at the ``yaml/`` root.

    Args:
        testcase_yaml_path: Absolute path to a ``test_*.yaml`` file.
        max_depth: Maximum directory levels to search upward (default 4).

    Returns:
        ``{"alias": {attrs...}, ...}`` from the ``elements`` key.

    Raises:
        ElementError: ``elements.yaml`` not found or contains no elements.
    """
    current_dir = testcase_yaml_path.parent
    searched = []

    for _ in range(max_depth + 1):
        candidate = current_dir / "elements.yaml"
        searched.append(str(candidate))
        if candidate.exists():
            raw = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
            if not isinstance(raw, dict):
                raise ElementError(
                    f"elements.yaml at {candidate} is not a valid YAML mapping."
                )

            elements: dict[str, dict[str, Any]] = raw.get("elements", {})
            if not elements:
                raise ElementError(
                    f"elements.yaml at {candidate} has no 'elements' defined."
                )
            return elements

        if current_dir.parent == current_dir:  # filesystem root
            break
        current_dir = current_dir.parent

    searched_summary = "\n  ".join(searched)
    raise ElementError(
        f"elements.yaml not found (searched up to {max_depth} levels):\n"
        f"  {searched_summary}\n"
        "Every YAML test case directory must have access to an elements.yaml "
        "that defines all element references used via 'ref'."
    )


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
