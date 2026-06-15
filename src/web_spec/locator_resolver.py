# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Resolve Web spec locators to Playwright locators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from web_spec.models import Locator as LocatorSpec
from web_spec.models import LocatorStrategy


class LocatorError(Exception):
    """Raised when a locator cannot be resolved safely."""


@dataclass
class ResolvedLocator:
    """Playwright locator plus metadata."""

    locator: Any
    strategy: str
    value: str
    match_count: int
    stability: str


def resolve_lazy(page: Any, spec: LocatorSpec) -> ResolvedLocator:
    """Resolve a locator without counting matches, for wait-like actions."""
    locator = _build_locator(page, spec)
    return ResolvedLocator(
        locator=locator.first,
        strategy=spec.strategy.value,
        value=spec.value,
        match_count=-1,
        stability=_stability(spec),
    )


def resolve(page: Any, spec: LocatorSpec, require_unique: bool = False) -> ResolvedLocator:
    """Resolve a locator and validate that at least one element matches."""
    locator = _build_locator(page, spec)
    count = locator.count()
    if count == 0:
        raise LocatorError(f"{spec.strategy.value}='{spec.value}' 匹配 0 个元素")
    if require_unique and count > 1 and not spec.first:
        raise LocatorError(
            f"{spec.strategy.value}='{spec.value}' 匹配 {count} 个元素；"
            "交互动作默认要求唯一匹配，如需取第一个请设置 locator.first: true"
        )
    return ResolvedLocator(
        locator=locator.first,
        strategy=spec.strategy.value,
        value=spec.value,
        match_count=count,
        stability=_stability(spec),
    )


def _build_locator(page: Any, spec: LocatorSpec):
    if spec.strategy == LocatorStrategy.ROLE:
        options = {"name": spec.name} if spec.name else {}
        return page.get_by_role(spec.value, **options)
    if spec.strategy == LocatorStrategy.TEXT:
        return page.get_by_text(spec.value, exact=spec.exact)
    if spec.strategy == LocatorStrategy.TEST_ID:
        return page.get_by_test_id(spec.value)
    if spec.strategy in (LocatorStrategy.BEM_CSS, LocatorStrategy.CSS):
        return page.locator(spec.value)
    raise LocatorError(f"未知的 locator strategy: {spec.strategy}")


def _stability(spec: LocatorSpec) -> str:
    if spec.strategy in (LocatorStrategy.ROLE, LocatorStrategy.TEXT, LocatorStrategy.TEST_ID):
        return "semantic"
    return spec.stability
