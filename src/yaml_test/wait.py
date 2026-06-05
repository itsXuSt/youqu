# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Conditional wait — polls AT-SPI tree until element appears."""

from __future__ import annotations

import time
from typing import Any, Union


def wait_for(
    selector: Union[dict, Any],
    timeout: int = 5000,
    interval: int = 200,
) -> bool:
    """Poll AT-SPI tree until element appears.

    Args:
        selector: Selector dict or Selector model with name/role/accessible_id.
        timeout: Max wait in milliseconds.
        interval: Poll interval in milliseconds.

    Returns:
        True if element found, False on timeout.
    """
    from src.yaml_test.executor import selector_to_expr

    if hasattr(selector, "model_dump"):
        sel_dict = selector.model_dump(exclude_none=True)
    elif isinstance(selector, dict):
        sel_dict = {k: v for k, v in selector.items() if v is not None}
    else:
        sel_dict = {}

    expr = selector_to_expr(sel_dict)
    if not expr or expr == "$/":
        return False

    from src.dogtail_utils import DogtailUtils

    dog = DogtailUtils()

    deadline = time.time() + timeout / 1000.0
    while time.time() < deadline:
        try:
            elements = dog.find_elements_by_attr(expr)
            if elements:
                return True
        except Exception:
            pass
        time.sleep(interval / 1000.0)
    return False
